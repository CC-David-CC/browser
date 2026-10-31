/* Source prepared for this handoff. Original adapter code: MIT (see LICENSE). Gecko remains MPL-2.0.
 * This file is compiled into the independent engine, not executed in host JS.
 * NOT COMPILED OR RUNTIME-TESTED IN THIS HANDOFF.
 */
#include "embed-xul.h"
#include <cstddef>
#include "nsWeakReference.h"
#include "nsIHttpChannel.h"

static_assert(sizeof(void*) == 4, "This mailbox ABI requires wasm32");
static_assert(offsetof(XulCmd, url) == 20, "ABI drift: url");
static_assert(offsetof(XulCmd, op) == 8212, "ABI drift: op");
static_assert(offsetof(XulCmd, cursor) == 8324, "ABI drift: cursor");
static_assert(sizeof(XulCmd) == 8328, "ABI drift: size");
extern "C" EMSCRIPTEN_KEEPALIVE int browser_embed_abi() { return 3; }

// Escape UTF-8 JSON text without running page JavaScript for browser chrome.
static std::string JsonText(const nsACString& text) {
  std::string out="\"";
  const char* data=text.BeginReading();
  const char* hex="0123456789abcdef";
  for (uint32_t i=0; i<text.Length(); ++i) {
    unsigned char c=static_cast<unsigned char>(data[i]);
    if (c=='"' || c=='\\') { out+='\\'; out+=static_cast<char>(c); }
    else if (c<0x20) { out+="\\u00"; out+=hex[c>>4]; out+=hex[c&15]; }
    else out+=static_cast<char>(c);
  }
  out+='"'; return out;
}

// Each Browser window has its own engine process and listener. Do not record
// request URLs: only top-level load state and the final HTTP status leave Gecko.
class BrowserProgressListener final : public nsIWebProgressListener, public nsSupportsWeakReference {
 public:
  NS_DECL_ISUPPORTS
  NS_DECL_NSIWEBPROGRESSLISTENER
 private:
  ~BrowserProgressListener() = default;
};
NS_IMPL_ISUPPORTS(BrowserProgressListener, nsIWebProgressListener, nsISupportsWeakReference)
static nsCOMPtr<nsIWebProgressListener> sProgressListener;
static uint32_t sProgressSequence = 0, sProgressStarts = 0, sProgressState = 0, sHttpStatus = 0;
static nsresult sProgressResult = NS_OK;
NS_IMETHODIMP BrowserProgressListener::OnStateChange(nsIWebProgress* progress, nsIRequest* request, uint32_t flags, nsresult status) {
  bool top = false;
  if (!progress || NS_FAILED(progress->GetIsTopLevel(&top)) || !top || !(flags & STATE_IS_NETWORK)) return NS_OK;
  if (flags & STATE_START) { ++sProgressStarts; ++sProgressSequence; sProgressState=1; sProgressResult=NS_OK; sHttpStatus=0; }
  if (flags & STATE_STOP) {
    ++sProgressSequence; sProgressState=2; sProgressResult=status; sHttpStatus=0;
    nsCOMPtr<nsIHttpChannel> channel=do_QueryInterface(request);
    uint32_t code=0;if(channel && NS_SUCCEEDED(channel->GetResponseStatus(&code)))sHttpStatus=code;
  }
  return NS_OK;
}
NS_IMETHODIMP BrowserProgressListener::OnProgressChange(nsIWebProgress*, nsIRequest*, int32_t, int32_t, int32_t, int32_t) { return NS_OK; }
NS_IMETHODIMP BrowserProgressListener::OnLocationChange(nsIWebProgress*, nsIRequest*, nsIURI*, uint32_t) { return NS_OK; }
NS_IMETHODIMP BrowserProgressListener::OnStatusChange(nsIWebProgress*, nsIRequest*, nsresult, const char16_t*) { return NS_OK; }
NS_IMETHODIMP BrowserProgressListener::OnSecurityChange(nsIWebProgress*, nsIRequest*, uint32_t) { return NS_OK; }
NS_IMETHODIMP BrowserProgressListener::OnContentBlockingEvent(nsIWebProgress*, nsIRequest*, uint32_t) { return NS_OK; }
static void AttachProgressListener() {
  if(sProgressListener || !g_docShell)return;
  nsCOMPtr<nsIWebProgress> progress=do_GetInterface(g_docShell);
  if(!progress)return;
  nsCOMPtr<nsIWebProgressListener> listener=new BrowserProgressListener();
  if(NS_SUCCEEDED(progress->AddProgressListener(listener,nsIWebProgress::NOTIFY_STATE_NETWORK)))sProgressListener=listener;
}

// Called by xul_load after creating the docshell, before starting a load.
uint32_t browser_progress_mark() { AttachProgressListener(); return sProgressStarts; }
bool browser_progress_failed_since(uint32_t mark) {
  // A redirect may cancel its preceding request; do not treat that as failure.
  return sProgressStarts!=mark && sProgressState==2 && NS_FAILED(sProgressResult) &&
         static_cast<uint32_t>(sProgressResult)!=0x804b0002u;
}

// 0 status, 1 back, 2 forward, 3 reload, 4 stop. Native navigation is authoritative.
char* browser_host_control(int action) {
  AttachProgressListener();
  nsCOMPtr<nsIWebNavigation> nav=do_QueryInterface(g_docShell);
  bool canBack=false,canForward=false;
  nsresult rv=NS_OK;
  if (nav) {
    nav->GetCanGoBack(&canBack);nav->GetCanGoForward(&canForward);
    switch(action) {
      case 0: break;
      case 1: if(canBack) rv=nav->GoBack(false,true); break;
      case 2: if(canForward) rv=nav->GoForward(false,true); break;
      case 3: rv=nav->Reload(nsIWebNavigation::LOAD_FLAGS_NONE); break;
      case 4: rv=nav->Stop(nsIWebNavigation::STOP_ALL); break;
      default: rv=NS_ERROR_INVALID_ARG; break;
    }
    if(action!=0) PumpEvents();
    nav->GetCanGoBack(&canBack);nav->GetCanGoForward(&canForward);
  } else if(action!=0) rv=NS_ERROR_NOT_AVAILABLE;
  nsAutoCString url;
  if(nav) { nsCOMPtr<nsIURI> uri;nav->GetCurrentURI(getter_AddRefs(uri));if(uri)uri->GetSpec(url); }
  std::string json="{\"progressReady\":"+(sProgressListener?std::string("true"):std::string("false"))+",\"sequence\":"+std::to_string(sProgressSequence)+",\"state\":"+std::to_string(sProgressState)+",\"result\":"+std::to_string(static_cast<uint32_t>(sProgressResult))+",\"httpStatus\":"+std::to_string(sHttpStatus)+",\"url\":"+JsonText(url)+",\"canGoBack\":"+(canBack?"true":"false")+
    ",\"canGoForward\":"+(canForward?"true":"false")+",\"ok\":"+(NS_SUCCEEDED(rv)?"true":"false")+"}";
  char* result=static_cast<char*>(malloc(json.size()+1));
  if(!result)return nullptr;
  memcpy(result,json.c_str(),json.size()+1);return result;
}

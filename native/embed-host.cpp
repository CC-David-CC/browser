/* Source prepared for this handoff. Original adapter code: MIT (see LICENSE). Gecko remains MPL-2.0.
 * This file is compiled into the independent engine, not executed in host JS.
 * NOT COMPILED OR RUNTIME-TESTED IN THIS HANDOFF.
 */
#include "embed-xul.h"
#include <cstddef>

static_assert(sizeof(void*) == 4, "This mailbox ABI requires wasm32");
static_assert(offsetof(XulCmd, url) == 20, "ABI drift: url");
static_assert(offsetof(XulCmd, op) == 8212, "ABI drift: op");
static_assert(offsetof(XulCmd, cursor) == 8324, "ABI drift: cursor");
static_assert(sizeof(XulCmd) == 8328, "ABI drift: size");
extern "C" EMSCRIPTEN_KEEPALIVE int browser_embed_abi() { return 1; }

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

// 0 status, 1 back, 2 forward, 3 reload, 4 stop. Native navigation is authoritative.
char* browser_host_control(int action) {
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
  std::string json="{\"url\":"+JsonText(url)+",\"canGoBack\":"+(canBack?"true":"false")+
    ",\"canGoForward\":"+(canForward?"true":"false")+",\"ok\":"+(NS_SUCCEEDED(rv)?"true":"false")+"}";
  char* result=static_cast<char*>(malloc(json.size()+1));
  if(!result)return nullptr;
  memcpy(result,json.c_str(),json.size()+1);return result;
}

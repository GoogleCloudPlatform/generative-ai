"use strict";(()=>{var Tn=function(t){let e=[],n=0;for(let r=0;r<t.length;r++){let i=t.charCodeAt(r);i<128?e[n++]=i:i<2048?(e[n++]=i>>6|192,e[n++]=i&63|128):(i&64512)===55296&&r+1<t.length&&(t.charCodeAt(r+1)&64512)===56320?(i=65536+((i&1023)<<10)+(t.charCodeAt(++r)&1023),e[n++]=i>>18|240,e[n++]=i>>12&63|128,e[n++]=i>>6&63|128,e[n++]=i&63|128):(e[n++]=i>>12|224,e[n++]=i>>6&63|128,e[n++]=i&63|128)}return e},pi=function(t){let e=[],n=0,r=0;for(;n<t.length;){let i=t[n++];if(i<128)e[r++]=String.fromCharCode(i);else if(i>191&&i<224){let s=t[n++];e[r++]=String.fromCharCode((i&31)<<6|s&63)}else if(i>239&&i<365){let s=t[n++],o=t[n++],a=t[n++],c=((i&7)<<18|(s&63)<<12|(o&63)<<6|a&63)-65536;e[r++]=String.fromCharCode(55296+(c>>10)),e[r++]=String.fromCharCode(56320+(c&1023))}else{let s=t[n++],o=t[n++];e[r++]=String.fromCharCode((i&15)<<12|(s&63)<<6|o&63)}}return e.join("")},bn={byteToCharMap_:null,charToByteMap_:null,byteToCharMapWebSafe_:null,charToByteMapWebSafe_:null,ENCODED_VALS_BASE:"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",get ENCODED_VALS(){return this.ENCODED_VALS_BASE+"+/="},get ENCODED_VALS_WEBSAFE(){return this.ENCODED_VALS_BASE+"-_."},HAS_NATIVE_SUPPORT:typeof atob=="function",encodeByteArray(t,e){if(!Array.isArray(t))throw Error("encodeByteArray takes an array as a parameter");this.init_();let n=e?this.byteToCharMapWebSafe_:this.byteToCharMap_,r=[];for(let i=0;i<t.length;i+=3){let s=t[i],o=i+1<t.length,a=o?t[i+1]:0,c=i+2<t.length,u=c?t[i+2]:0,d=s>>2,f=(s&3)<<4|a>>4,_=(a&15)<<2|u>>6,R=u&63;c||(R=64,o||(_=64)),r.push(n[d],n[f],n[_],n[R])}return r.join("")},encodeString(t,e){return this.HAS_NATIVE_SUPPORT&&!e?btoa(t):this.encodeByteArray(Tn(t),e)},decodeString(t,e){return this.HAS_NATIVE_SUPPORT&&!e?atob(t):pi(this.decodeStringToByteArray(t,e))},decodeStringToByteArray(t,e){this.init_();let n=e?this.charToByteMapWebSafe_:this.charToByteMap_,r=[];for(let i=0;i<t.length;){let s=n[t.charAt(i++)],a=i<t.length?n[t.charAt(i)]:0;++i;let u=i<t.length?n[t.charAt(i)]:64;++i;let f=i<t.length?n[t.charAt(i)]:64;if(++i,s==null||a==null||u==null||f==null)throw new dt;let _=s<<2|a>>4;if(r.push(_),u!==64){let R=a<<4&240|u>>2;if(r.push(R),f!==64){let J=u<<6&192|f;r.push(J)}}}return r},init_(){if(!this.byteToCharMap_){this.byteToCharMap_={},this.charToByteMap_={},this.byteToCharMapWebSafe_={},this.charToByteMapWebSafe_={};for(let t=0;t<this.ENCODED_VALS.length;t++)this.byteToCharMap_[t]=this.ENCODED_VALS.charAt(t),this.charToByteMap_[this.byteToCharMap_[t]]=t,this.byteToCharMapWebSafe_[t]=this.ENCODED_VALS_WEBSAFE.charAt(t),this.charToByteMapWebSafe_[this.byteToCharMapWebSafe_[t]]=t,t>=this.ENCODED_VALS_BASE.length&&(this.charToByteMap_[this.ENCODED_VALS_WEBSAFE.charAt(t)]=t,this.charToByteMapWebSafe_[this.ENCODED_VALS.charAt(t)]=t)}}},dt=class extends Error{constructor(){super(...arguments),this.name="DecodeBase64StringError"}},mi=function(t){let e=Tn(t);return bn.encodeByteArray(e,!0)},ft=function(t){return mi(t).replace(/\./g,"")},pt=function(t){try{return bn.decodeString(t,!0)}catch(e){console.error("base64Decode failed: ",e)}return null};function gi(){if(typeof self<"u")return self;if(typeof window<"u")return window;if(typeof global<"u")return global;throw new Error("Unable to locate global object.")}var _i=()=>gi().__FIREBASE_DEFAULTS__,Ii=()=>{if(typeof process>"u"||typeof process.env>"u")return;let t=process.env.__FIREBASE_DEFAULTS__;if(t)return JSON.parse(t)},vi=()=>{if(typeof document>"u")return;let t;try{t=document.cookie.match(/__FIREBASE_DEFAULTS__=([^;]+)/)}catch{return}let e=t&&pt(t[1]);return e&&JSON.parse(e)},mt=()=>{try{return _i()||Ii()||vi()}catch(t){console.info(`Unable to get __FIREBASE_DEFAULTS__ due to: ${t}`);return}},An=t=>{var e,n;return(n=(e=mt())===null||e===void 0?void 0:e.emulatorHosts)===null||n===void 0?void 0:n[t]};var gt=()=>{var t;return(t=mt())===null||t===void 0?void 0:t.config},_t=t=>{var e;return(e=mt())===null||e===void 0?void 0:e[`_${t}`]};var Ee=class{constructor(){this.reject=()=>{},this.resolve=()=>{},this.promise=new Promise((e,n)=>{this.resolve=e,this.reject=n})}wrapCallback(e){return(n,r)=>{n?this.reject(n):this.resolve(r),typeof e=="function"&&(this.promise.catch(()=>{}),e.length===1?e(n):e(n,r))}}};function m(){return typeof navigator<"u"&&typeof navigator.userAgent=="string"?navigator.userAgent:""}function Sn(){return typeof window<"u"&&!!(window.cordova||window.phonegap||window.PhoneGap)&&/ios|iphone|ipod|ipad|android|blackberry|iemobile/i.test(m())}function Rn(){return typeof navigator<"u"&&navigator.userAgent==="Cloudflare-Workers"}function On(){let t=typeof chrome=="object"?chrome.runtime:typeof browser=="object"?browser.runtime:void 0;return typeof t=="object"&&t.id!==void 0}function kn(){return typeof navigator=="object"&&navigator.product==="ReactNative"}function Pn(){let t=m();return t.indexOf("MSIE ")>=0||t.indexOf("Trident/")>=0}function Cn(){try{return typeof indexedDB=="object"}catch{return!1}}function Nn(){return new Promise((t,e)=>{try{let n=!0,r="validate-browser-context-for-indexeddb-analytics-module",i=self.indexedDB.open(r);i.onsuccess=()=>{i.result.close(),n||self.indexedDB.deleteDatabase(r),t(!0)},i.onupgradeneeded=()=>{n=!1},i.onerror=()=>{var s;e(((s=i.error)===null||s===void 0?void 0:s.message)||"")}}catch(n){e(n)}})}var yi="FirebaseError",I=class t extends Error{constructor(e,n,r){super(n),this.code=e,this.customData=r,this.name=yi,Object.setPrototypeOf(this,t.prototype),Error.captureStackTrace&&Error.captureStackTrace(this,y.prototype.create)}},y=class{constructor(e,n,r){this.service=e,this.serviceName=n,this.errors=r}create(e,...n){let r=n[0]||{},i=`${this.service}/${e}`,s=this.errors[e],o=s?Ei(s,r):"Error",a=`${this.serviceName}: ${o} (${i}).`;return new I(i,a,r)}};function Ei(t,e){return t.replace(wi,(n,r)=>{let i=e[r];return i!=null?String(i):`<${r}?>`})}var wi=/\{\$([^}]+)}/g;function Dn(t){for(let e in t)if(Object.prototype.hasOwnProperty.call(t,e))return!1;return!0}function Y(t,e){if(t===e)return!0;let n=Object.keys(t),r=Object.keys(e);for(let i of n){if(!r.includes(i))return!1;let s=t[i],o=e[i];if(wn(s)&&wn(o)){if(!Y(s,o))return!1}else if(s!==o)return!1}for(let i of r)if(!n.includes(i))return!1;return!0}function wn(t){return t!==null&&typeof t=="object"}function X(t){let e=[];for(let[n,r]of Object.entries(t))Array.isArray(r)?r.forEach(i=>{e.push(encodeURIComponent(n)+"="+encodeURIComponent(i))}):e.push(encodeURIComponent(n)+"="+encodeURIComponent(r));return e.length?"&"+e.join("&"):""}function Q(t){let e={};return t.replace(/^\?/,"").split("&").forEach(r=>{if(r){let[i,s]=r.split("=");e[decodeURIComponent(i)]=decodeURIComponent(s)}}),e}function Z(t){let e=t.indexOf("?");if(!e)return"";let n=t.indexOf("#",e);return t.substring(e,n>0?n:void 0)}function Ln(t,e){let n=new ht(t,e);return n.subscribe.bind(n)}var ht=class{constructor(e,n){this.observers=[],this.unsubscribes=[],this.observerCount=0,this.task=Promise.resolve(),this.finalized=!1,this.onNoObservers=n,this.task.then(()=>{e(this)}).catch(r=>{this.error(r)})}next(e){this.forEachObserver(n=>{n.next(e)})}error(e){this.forEachObserver(n=>{n.error(e)}),this.close(e)}complete(){this.forEachObserver(e=>{e.complete()}),this.close()}subscribe(e,n,r){let i;if(e===void 0&&n===void 0&&r===void 0)throw new Error("Missing Observer.");Ti(e,["next","error","complete"])?i=e:i={next:e,error:n,complete:r},i.next===void 0&&(i.next=lt),i.error===void 0&&(i.error=lt),i.complete===void 0&&(i.complete=lt);let s=this.unsubscribeOne.bind(this,this.observers.length);return this.finalized&&this.task.then(()=>{try{this.finalError?i.error(this.finalError):i.complete()}catch{}}),this.observers.push(i),s}unsubscribeOne(e){this.observers===void 0||this.observers[e]===void 0||(delete this.observers[e],this.observerCount-=1,this.observerCount===0&&this.onNoObservers!==void 0&&this.onNoObservers(this))}forEachObserver(e){if(!this.finalized)for(let n=0;n<this.observers.length;n++)this.sendOne(n,e)}sendOne(e,n){this.task.then(()=>{if(this.observers!==void 0&&this.observers[e]!==void 0)try{n(this.observers[e])}catch(r){typeof console<"u"&&console.error&&console.error(r)}})}close(e){this.finalized||(this.finalized=!0,e!==void 0&&(this.finalError=e),this.task.then(()=>{this.observers=void 0,this.onNoObservers=void 0}))}};function Ti(t,e){if(typeof t!="object"||t===null)return!1;for(let n of e)if(n in t&&typeof t[n]=="function")return!0;return!1}function lt(){}var dc=4*60*60*1e3;function O(t){return t&&t._delegate?t._delegate:t}var v=class{constructor(e,n,r){this.name=e,this.instanceFactory=n,this.type=r,this.multipleInstances=!1,this.serviceProps={},this.instantiationMode="LAZY",this.onInstanceCreated=null}setInstantiationMode(e){return this.instantiationMode=e,this}setMultipleInstances(e){return this.multipleInstances=e,this}setServiceProps(e){return this.serviceProps=e,this}setInstanceCreatedCallback(e){return this.onInstanceCreated=e,this}};var U="[DEFAULT]";var It=class{constructor(e,n){this.name=e,this.container=n,this.component=null,this.instances=new Map,this.instancesDeferred=new Map,this.instancesOptions=new Map,this.onInitCallbacks=new Map}get(e){let n=this.normalizeInstanceIdentifier(e);if(!this.instancesDeferred.has(n)){let r=new Ee;if(this.instancesDeferred.set(n,r),this.isInitialized(n)||this.shouldAutoInitialize())try{let i=this.getOrInitializeService({instanceIdentifier:n});i&&r.resolve(i)}catch{}}return this.instancesDeferred.get(n).promise}getImmediate(e){var n;let r=this.normalizeInstanceIdentifier(e?.identifier),i=(n=e?.optional)!==null&&n!==void 0?n:!1;if(this.isInitialized(r)||this.shouldAutoInitialize())try{return this.getOrInitializeService({instanceIdentifier:r})}catch(s){if(i)return null;throw s}else{if(i)return null;throw Error(`Service ${this.name} is not available`)}}getComponent(){return this.component}setComponent(e){if(e.name!==this.name)throw Error(`Mismatching Component ${e.name} for Provider ${this.name}.`);if(this.component)throw Error(`Component for ${this.name} has already been provided`);if(this.component=e,!!this.shouldAutoInitialize()){if(Ai(e))try{this.getOrInitializeService({instanceIdentifier:U})}catch{}for(let[n,r]of this.instancesDeferred.entries()){let i=this.normalizeInstanceIdentifier(n);try{let s=this.getOrInitializeService({instanceIdentifier:i});r.resolve(s)}catch{}}}}clearInstance(e=U){this.instancesDeferred.delete(e),this.instancesOptions.delete(e),this.instances.delete(e)}async delete(){let e=Array.from(this.instances.values());await Promise.all([...e.filter(n=>"INTERNAL"in n).map(n=>n.INTERNAL.delete()),...e.filter(n=>"_delete"in n).map(n=>n._delete())])}isComponentSet(){return this.component!=null}isInitialized(e=U){return this.instances.has(e)}getOptions(e=U){return this.instancesOptions.get(e)||{}}initialize(e={}){let{options:n={}}=e,r=this.normalizeInstanceIdentifier(e.instanceIdentifier);if(this.isInitialized(r))throw Error(`${this.name}(${r}) has already been initialized`);if(!this.isComponentSet())throw Error(`Component ${this.name} has not been registered yet`);let i=this.getOrInitializeService({instanceIdentifier:r,options:n});for(let[s,o]of this.instancesDeferred.entries()){let a=this.normalizeInstanceIdentifier(s);r===a&&o.resolve(i)}return i}onInit(e,n){var r;let i=this.normalizeInstanceIdentifier(n),s=(r=this.onInitCallbacks.get(i))!==null&&r!==void 0?r:new Set;s.add(e),this.onInitCallbacks.set(i,s);let o=this.instances.get(i);return o&&e(o,i),()=>{s.delete(e)}}invokeOnInitCallbacks(e,n){let r=this.onInitCallbacks.get(n);if(r)for(let i of r)try{i(e,n)}catch{}}getOrInitializeService({instanceIdentifier:e,options:n={}}){let r=this.instances.get(e);if(!r&&this.component&&(r=this.component.instanceFactory(this.container,{instanceIdentifier:bi(e),options:n}),this.instances.set(e,r),this.instancesOptions.set(e,n),this.invokeOnInitCallbacks(r,e),this.component.onInstanceCreated))try{this.component.onInstanceCreated(this.container,e,r)}catch{}return r||null}normalizeInstanceIdentifier(e=U){return this.component?this.component.multipleInstances?e:U:e}shouldAutoInitialize(){return!!this.component&&this.component.instantiationMode!=="EXPLICIT"}};function bi(t){return t===U?void 0:t}function Ai(t){return t.instantiationMode==="EAGER"}var we=class{constructor(e){this.name=e,this.providers=new Map}addComponent(e){let n=this.getProvider(e.name);if(n.isComponentSet())throw new Error(`Component ${e.name} has already been registered with ${this.name}`);n.setComponent(e)}addOrOverwriteComponent(e){this.getProvider(e.name).isComponentSet()&&this.providers.delete(e.name),this.addComponent(e)}getProvider(e){if(this.providers.has(e))return this.providers.get(e);let n=new It(e,this);return this.providers.set(e,n),n}getProviders(){return Array.from(this.providers.values())}};var Si=[],h;(function(t){t[t.DEBUG=0]="DEBUG",t[t.VERBOSE=1]="VERBOSE",t[t.INFO=2]="INFO",t[t.WARN=3]="WARN",t[t.ERROR=4]="ERROR",t[t.SILENT=5]="SILENT"})(h||(h={}));var Ri={debug:h.DEBUG,verbose:h.VERBOSE,info:h.INFO,warn:h.WARN,error:h.ERROR,silent:h.SILENT},Oi=h.INFO,ki={[h.DEBUG]:"log",[h.VERBOSE]:"log",[h.INFO]:"info",[h.WARN]:"warn",[h.ERROR]:"error"},Pi=(t,e,...n)=>{if(e<t.logLevel)return;let r=new Date().toISOString(),i=ki[e];if(i)console[i](`[${r}]  ${t.name}:`,...n);else throw new Error(`Attempted to log a message with an invalid logType (value: ${e})`)},ee=class{constructor(e){this.name=e,this._logLevel=Oi,this._logHandler=Pi,this._userLogHandler=null,Si.push(this)}get logLevel(){return this._logLevel}set logLevel(e){if(!(e in h))throw new TypeError(`Invalid value "${e}" assigned to \`logLevel\``);this._logLevel=e}setLogLevel(e){this._logLevel=typeof e=="string"?Ri[e]:e}get logHandler(){return this._logHandler}set logHandler(e){if(typeof e!="function")throw new TypeError("Value assigned to `logHandler` must be a function");this._logHandler=e}get userLogHandler(){return this._userLogHandler}set userLogHandler(e){this._userLogHandler=e}debug(...e){this._userLogHandler&&this._userLogHandler(this,h.DEBUG,...e),this._logHandler(this,h.DEBUG,...e)}log(...e){this._userLogHandler&&this._userLogHandler(this,h.VERBOSE,...e),this._logHandler(this,h.VERBOSE,...e)}info(...e){this._userLogHandler&&this._userLogHandler(this,h.INFO,...e),this._logHandler(this,h.INFO,...e)}warn(...e){this._userLogHandler&&this._userLogHandler(this,h.WARN,...e),this._logHandler(this,h.WARN,...e)}error(...e){this._userLogHandler&&this._userLogHandler(this,h.ERROR,...e),this._logHandler(this,h.ERROR,...e)}};var Ci=(t,e)=>e.some(n=>t instanceof n),Mn,Un;function Ni(){return Mn||(Mn=[IDBDatabase,IDBObjectStore,IDBIndex,IDBCursor,IDBTransaction])}function Di(){return Un||(Un=[IDBCursor.prototype.advance,IDBCursor.prototype.continue,IDBCursor.prototype.continuePrimaryKey])}var xn=new WeakMap,yt=new WeakMap,Fn=new WeakMap,vt=new WeakMap,wt=new WeakMap;function Li(t){let e=new Promise((n,r)=>{let i=()=>{t.removeEventListener("success",s),t.removeEventListener("error",o)},s=()=>{n(T(t.result)),i()},o=()=>{r(t.error),i()};t.addEventListener("success",s),t.addEventListener("error",o)});return e.then(n=>{n instanceof IDBCursor&&xn.set(n,t)}).catch(()=>{}),wt.set(e,t),e}function Mi(t){if(yt.has(t))return;let e=new Promise((n,r)=>{let i=()=>{t.removeEventListener("complete",s),t.removeEventListener("error",o),t.removeEventListener("abort",o)},s=()=>{n(),i()},o=()=>{r(t.error||new DOMException("AbortError","AbortError")),i()};t.addEventListener("complete",s),t.addEventListener("error",o),t.addEventListener("abort",o)});yt.set(t,e)}var Et={get(t,e,n){if(t instanceof IDBTransaction){if(e==="done")return yt.get(t);if(e==="objectStoreNames")return t.objectStoreNames||Fn.get(t);if(e==="store")return n.objectStoreNames[1]?void 0:n.objectStore(n.objectStoreNames[0])}return T(t[e])},set(t,e,n){return t[e]=n,!0},has(t,e){return t instanceof IDBTransaction&&(e==="done"||e==="store")?!0:e in t}};function Vn(t){Et=t(Et)}function Ui(t){return t===IDBDatabase.prototype.transaction&&!("objectStoreNames"in IDBTransaction.prototype)?function(e,...n){let r=t.call(Te(this),e,...n);return Fn.set(r,e.sort?e.sort():[e]),T(r)}:Di().includes(t)?function(...e){return t.apply(Te(this),e),T(xn.get(this))}:function(...e){return T(t.apply(Te(this),e))}}function xi(t){return typeof t=="function"?Ui(t):(t instanceof IDBTransaction&&Mi(t),Ci(t,Ni())?new Proxy(t,Et):t)}function T(t){if(t instanceof IDBRequest)return Li(t);if(vt.has(t))return vt.get(t);let e=xi(t);return e!==t&&(vt.set(t,e),wt.set(e,t)),e}var Te=t=>wt.get(t);function be(t,e,{blocked:n,upgrade:r,blocking:i,terminated:s}={}){let o=indexedDB.open(t,e),a=T(o);return r&&o.addEventListener("upgradeneeded",c=>{r(T(o.result),c.oldVersion,c.newVersion,T(o.transaction),c)}),n&&o.addEventListener("blocked",c=>n(c.oldVersion,c.newVersion,c)),a.then(c=>{s&&c.addEventListener("close",()=>s()),i&&c.addEventListener("versionchange",u=>i(u.oldVersion,u.newVersion,u))}).catch(()=>{}),a}var Fi=["get","getKey","getAll","getAllKeys","count"],Vi=["put","add","delete","clear"],Tt=new Map;function jn(t,e){if(!(t instanceof IDBDatabase&&!(e in t)&&typeof e=="string"))return;if(Tt.get(e))return Tt.get(e);let n=e.replace(/FromIndex$/,""),r=e!==n,i=Vi.includes(n);if(!(n in(r?IDBIndex:IDBObjectStore).prototype)||!(i||Fi.includes(n)))return;let s=async function(o,...a){let c=this.transaction(o,i?"readwrite":"readonly"),u=c.store;return r&&(u=u.index(a.shift())),(await Promise.all([u[n](...a),i&&c.done]))[0]};return Tt.set(e,s),s}Vn(t=>({...t,get:(e,n,r)=>jn(e,n)||t.get(e,n,r),has:(e,n)=>!!jn(e,n)||t.has(e,n)}));var At=class{constructor(e){this.container=e}getPlatformInfoString(){return this.container.getProviders().map(n=>{if(ji(n)){let r=n.getImmediate();return`${r.library}/${r.version}`}else return null}).filter(n=>n).join(" ")}};function ji(t){let e=t.getComponent();return e?.type==="VERSION"}var St="@firebase/app",Hn="0.10.11";var k=new ee("@firebase/app"),Hi="@firebase/app-compat",Wi="@firebase/analytics-compat",Bi="@firebase/analytics",$i="@firebase/app-check-compat",qi="@firebase/app-check",zi="@firebase/auth",Gi="@firebase/auth-compat",Ki="@firebase/database",Ji="@firebase/database-compat",Yi="@firebase/functions",Xi="@firebase/functions-compat",Qi="@firebase/installations",Zi="@firebase/installations-compat",es="@firebase/messaging",ts="@firebase/messaging-compat",ns="@firebase/performance",rs="@firebase/performance-compat",is="@firebase/remote-config",ss="@firebase/remote-config-compat",os="@firebase/storage",as="@firebase/storage-compat",cs="@firebase/firestore",us="@firebase/vertexai-preview",ls="@firebase/firestore-compat",ds="firebase",hs="10.13.2";var Rt="[DEFAULT]",fs={[St]:"fire-core",[Hi]:"fire-core-compat",[Bi]:"fire-analytics",[Wi]:"fire-analytics-compat",[qi]:"fire-app-check",[$i]:"fire-app-check-compat",[zi]:"fire-auth",[Gi]:"fire-auth-compat",[Ki]:"fire-rtdb",[Ji]:"fire-rtdb-compat",[Yi]:"fire-fn",[Xi]:"fire-fn-compat",[Qi]:"fire-iid",[Zi]:"fire-iid-compat",[es]:"fire-fcm",[ts]:"fire-fcm-compat",[ns]:"fire-perf",[rs]:"fire-perf-compat",[is]:"fire-rc",[ss]:"fire-rc-compat",[os]:"fire-gcs",[as]:"fire-gcs-compat",[cs]:"fire-fst",[ls]:"fire-fst-compat",[us]:"fire-vertex","fire-js":"fire-js",[ds]:"fire-js-all"};var Ae=new Map,ps=new Map,Ot=new Map;function Wn(t,e){try{t.container.addComponent(e)}catch(n){k.debug(`Component ${e.name} failed to register with FirebaseApp ${t.name}`,n)}}function P(t){let e=t.name;if(Ot.has(e))return k.debug(`There were multiple attempts to register component ${e}.`),!1;Ot.set(e,t);for(let n of Ae.values())Wn(n,t);for(let n of ps.values())Wn(n,t);return!0}function x(t,e){let n=t.container.getProvider("heartbeat").getImmediate({optional:!0});return n&&n.triggerHeartbeat(),t.container.getProvider(e)}function C(t){return t.settings!==void 0}var ms={"no-app":"No Firebase App '{$appName}' has been created - call initializeApp() first","bad-app-name":"Illegal App name: '{$appName}'","duplicate-app":"Firebase App named '{$appName}' already exists with different options or config","app-deleted":"Firebase App named '{$appName}' already deleted","server-app-deleted":"Firebase Server App has been deleted","no-options":"Need to provide options, when not being deployed to hosting via source.","invalid-app-argument":"firebase.{$appName}() takes either no argument or a Firebase App instance.","invalid-log-argument":"First argument to `onLog` must be null or a function.","idb-open":"Error thrown when opening IndexedDB. Original error: {$originalErrorMessage}.","idb-get":"Error thrown when reading from IndexedDB. Original error: {$originalErrorMessage}.","idb-set":"Error thrown when writing to IndexedDB. Original error: {$originalErrorMessage}.","idb-delete":"Error thrown when deleting from IndexedDB. Original error: {$originalErrorMessage}.","finalization-registry-not-supported":"FirebaseServerApp deleteOnDeref field defined but the JS runtime does not support FinalizationRegistry.","invalid-server-app-environment":"FirebaseServerApp is not for use in browser environments."},L=new y("app","Firebase",ms);var kt=class{constructor(e,n,r){this._isDeleted=!1,this._options=Object.assign({},e),this._config=Object.assign({},n),this._name=n.name,this._automaticDataCollectionEnabled=n.automaticDataCollectionEnabled,this._container=r,this.container.addComponent(new v("app",()=>this,"PUBLIC"))}get automaticDataCollectionEnabled(){return this.checkDestroyed(),this._automaticDataCollectionEnabled}set automaticDataCollectionEnabled(e){this.checkDestroyed(),this._automaticDataCollectionEnabled=e}get name(){return this.checkDestroyed(),this._name}get options(){return this.checkDestroyed(),this._options}get config(){return this.checkDestroyed(),this._config}get container(){return this._container}get isDeleted(){return this._isDeleted}set isDeleted(e){this._isDeleted=e}checkDestroyed(){if(this.isDeleted)throw L.create("app-deleted",{appName:this._name})}};var te=hs;function Nt(t,e={}){let n=t;typeof e!="object"&&(e={name:e});let r=Object.assign({name:Rt,automaticDataCollectionEnabled:!1},e),i=r.name;if(typeof i!="string"||!i)throw L.create("bad-app-name",{appName:String(i)});if(n||(n=gt()),!n)throw L.create("no-options");let s=Ae.get(i);if(s){if(Y(n,s.options)&&Y(r,s.config))return s;throw L.create("duplicate-app",{appName:i})}let o=new we(i);for(let c of Ot.values())o.addComponent(c);let a=new kt(n,r,o);return Ae.set(i,a),a}function Se(t=Rt){let e=Ae.get(t);if(!e&&t===Rt&&gt())return Nt();if(!e)throw L.create("no-app",{appName:t});return e}function E(t,e,n){var r;let i=(r=fs[t])!==null&&r!==void 0?r:t;n&&(i+=`-${n}`);let s=i.match(/\s|\//),o=e.match(/\s|\//);if(s||o){let a=[`Unable to register library "${i}" with version "${e}":`];s&&a.push(`library name "${i}" contains illegal characters (whitespace or "/")`),s&&o&&a.push("and"),o&&a.push(`version name "${e}" contains illegal characters (whitespace or "/")`),k.warn(a.join(" "));return}P(new v(`${i}-version`,()=>({library:i,version:e}),"VERSION"))}var gs="firebase-heartbeat-database",_s=1,se="firebase-heartbeat-store",bt=null;function zn(){return bt||(bt=be(gs,_s,{upgrade:(t,e)=>{switch(e){case 0:try{t.createObjectStore(se)}catch(n){console.warn(n)}}}}).catch(t=>{throw L.create("idb-open",{originalErrorMessage:t.message})})),bt}async function Is(t){try{let n=(await zn()).transaction(se),r=await n.objectStore(se).get(Gn(t));return await n.done,r}catch(e){if(e instanceof I)k.warn(e.message);else{let n=L.create("idb-get",{originalErrorMessage:e?.message});k.warn(n.message)}}}async function Bn(t,e){try{let r=(await zn()).transaction(se,"readwrite");await r.objectStore(se).put(e,Gn(t)),await r.done}catch(n){if(n instanceof I)k.warn(n.message);else{let r=L.create("idb-set",{originalErrorMessage:n?.message});k.warn(r.message)}}}function Gn(t){return`${t.name}!${t.options.appId}`}var vs=1024,ys=30*24*60*60*1e3,Pt=class{constructor(e){this.container=e,this._heartbeatsCache=null;let n=this.container.getProvider("app").getImmediate();this._storage=new Ct(n),this._heartbeatsCachePromise=this._storage.read().then(r=>(this._heartbeatsCache=r,r))}async triggerHeartbeat(){var e,n;try{let i=this.container.getProvider("platform-logger").getImmediate().getPlatformInfoString(),s=$n();return((e=this._heartbeatsCache)===null||e===void 0?void 0:e.heartbeats)==null&&(this._heartbeatsCache=await this._heartbeatsCachePromise,((n=this._heartbeatsCache)===null||n===void 0?void 0:n.heartbeats)==null)||this._heartbeatsCache.lastSentHeartbeatDate===s||this._heartbeatsCache.heartbeats.some(o=>o.date===s)?void 0:(this._heartbeatsCache.heartbeats.push({date:s,agent:i}),this._heartbeatsCache.heartbeats=this._heartbeatsCache.heartbeats.filter(o=>{let a=new Date(o.date).valueOf();return Date.now()-a<=ys}),this._storage.overwrite(this._heartbeatsCache))}catch(r){k.warn(r)}}async getHeartbeatsHeader(){var e;try{if(this._heartbeatsCache===null&&await this._heartbeatsCachePromise,((e=this._heartbeatsCache)===null||e===void 0?void 0:e.heartbeats)==null||this._heartbeatsCache.heartbeats.length===0)return"";let n=$n(),{heartbeatsToSend:r,unsentEntries:i}=Es(this._heartbeatsCache.heartbeats),s=ft(JSON.stringify({version:2,heartbeats:r}));return this._heartbeatsCache.lastSentHeartbeatDate=n,i.length>0?(this._heartbeatsCache.heartbeats=i,await this._storage.overwrite(this._heartbeatsCache)):(this._heartbeatsCache.heartbeats=[],this._storage.overwrite(this._heartbeatsCache)),s}catch(n){return k.warn(n),""}}};function $n(){return new Date().toISOString().substring(0,10)}function Es(t,e=vs){let n=[],r=t.slice();for(let i of t){let s=n.find(o=>o.agent===i.agent);if(s){if(s.dates.push(i.date),qn(n)>e){s.dates.pop();break}}else if(n.push({agent:i.agent,dates:[i.date]}),qn(n)>e){n.pop();break}r=r.slice(1)}return{heartbeatsToSend:n,unsentEntries:r}}var Ct=class{constructor(e){this.app=e,this._canUseIndexedDBPromise=this.runIndexedDBEnvironmentCheck()}async runIndexedDBEnvironmentCheck(){return Cn()?Nn().then(()=>!0).catch(()=>!1):!1}async read(){if(await this._canUseIndexedDBPromise){let n=await Is(this.app);return n?.heartbeats?n:{heartbeats:[]}}else return{heartbeats:[]}}async overwrite(e){var n;if(await this._canUseIndexedDBPromise){let i=await this.read();return Bn(this.app,{lastSentHeartbeatDate:(n=e.lastSentHeartbeatDate)!==null&&n!==void 0?n:i.lastSentHeartbeatDate,heartbeats:e.heartbeats})}else return}async add(e){var n;if(await this._canUseIndexedDBPromise){let i=await this.read();return Bn(this.app,{lastSentHeartbeatDate:(n=e.lastSentHeartbeatDate)!==null&&n!==void 0?n:i.lastSentHeartbeatDate,heartbeats:[...i.heartbeats,...e.heartbeats]})}else return}};function qn(t){return ft(JSON.stringify({version:2,heartbeats:t})).length}function ws(t){P(new v("platform-logger",e=>new At(e),"PRIVATE")),P(new v("heartbeat",e=>new Pt(e),"PRIVATE")),E(St,Hn,t),E(St,Hn,"esm2017"),E("fire-js","")}ws("");var Ts="firebase",bs="10.13.2";E(Ts,bs,"app");function Re(t,e){var n={};for(var r in t)Object.prototype.hasOwnProperty.call(t,r)&&e.indexOf(r)<0&&(n[r]=t[r]);if(t!=null&&typeof Object.getOwnPropertySymbols=="function")for(var i=0,r=Object.getOwnPropertySymbols(t);i<r.length;i++)e.indexOf(r[i])<0&&Object.prototype.propertyIsEnumerable.call(t,r[i])&&(n[r[i]]=t[r[i]]);return n}function dr(){return{"dependent-sdk-initialized-before-auth":"Another Firebase SDK was initialized and is trying to use Auth before Auth is initialized. Please be sure to call `initializeAuth` or `getAuth` before starting any other Firebase SDK."}}var hr=dr,fr=new y("auth","Firebase",dr());var De=new ee("@firebase/auth");function As(t,...e){De.logLevel<=h.WARN&&De.warn(`Auth (${te}): ${t}`,...e)}function ke(t,...e){De.logLevel<=h.ERROR&&De.error(`Auth (${te}): ${t}`,...e)}function w(t,...e){throw Zt(t,...e)}function A(t,...e){return Zt(t,...e)}function pr(t,e,n){let r=Object.assign(Object.assign({},hr()),{[e]:n});return new y("auth","Firebase",r).create(e,{appName:t.name})}function F(t){return pr(t,"operation-not-supported-in-this-environment","Operations that alter the current user are not supported in conjunction with FirebaseServerApp")}function Zt(t,...e){if(typeof t!="string"){let n=e[0],r=[...e.slice(1)];return r[0]&&(r[0].appName=t.name),t._errorFactory.create(n,...r)}return fr.create(t,...e)}function l(t,e,...n){if(!t)throw Zt(e,...n)}function b(t){let e="INTERNAL ASSERTION FAILED: "+t;throw ke(e),new Error(e)}function D(t,e){t||b(e)}function Mt(){var t;return typeof self<"u"&&((t=self.location)===null||t===void 0?void 0:t.href)||""}function Ss(){return Kn()==="http:"||Kn()==="https:"}function Kn(){var t;return typeof self<"u"&&((t=self.location)===null||t===void 0?void 0:t.protocol)||null}function Rs(){return typeof navigator<"u"&&navigator&&"onLine"in navigator&&typeof navigator.onLine=="boolean"&&(Ss()||On()||"connection"in navigator)?navigator.onLine:!0}function Os(){if(typeof navigator>"u")return null;let t=navigator;return t.languages&&t.languages[0]||t.language||null}var V=class{constructor(e,n){this.shortDelay=e,this.longDelay=n,D(n>e,"Short delay should be less than long delay!"),this.isMobile=Sn()||kn()}get(){return Rs()?this.isMobile?this.longDelay:this.shortDelay:Math.min(5e3,this.shortDelay)}};function en(t,e){D(t.emulator,"Emulator should always be set here");let{url:n}=t.emulator;return e?`${n}${e.startsWith("/")?e.slice(1):e}`:n}var Le=class{static initialize(e,n,r){this.fetchImpl=e,n&&(this.headersImpl=n),r&&(this.responseImpl=r)}static fetch(){if(this.fetchImpl)return this.fetchImpl;if(typeof self<"u"&&"fetch"in self)return self.fetch;if(typeof globalThis<"u"&&globalThis.fetch)return globalThis.fetch;if(typeof fetch<"u")return fetch;b("Could not find fetch implementation, make sure you call FetchProvider.initialize() with an appropriate polyfill")}static headers(){if(this.headersImpl)return this.headersImpl;if(typeof self<"u"&&"Headers"in self)return self.Headers;if(typeof globalThis<"u"&&globalThis.Headers)return globalThis.Headers;if(typeof Headers<"u")return Headers;b("Could not find Headers implementation, make sure you call FetchProvider.initialize() with an appropriate polyfill")}static response(){if(this.responseImpl)return this.responseImpl;if(typeof self<"u"&&"Response"in self)return self.Response;if(typeof globalThis<"u"&&globalThis.Response)return globalThis.Response;if(typeof Response<"u")return Response;b("Could not find Response implementation, make sure you call FetchProvider.initialize() with an appropriate polyfill")}};var ks={CREDENTIAL_MISMATCH:"custom-token-mismatch",MISSING_CUSTOM_TOKEN:"internal-error",INVALID_IDENTIFIER:"invalid-email",MISSING_CONTINUE_URI:"internal-error",INVALID_PASSWORD:"wrong-password",MISSING_PASSWORD:"missing-password",INVALID_LOGIN_CREDENTIALS:"invalid-credential",EMAIL_EXISTS:"email-already-in-use",PASSWORD_LOGIN_DISABLED:"operation-not-allowed",INVALID_IDP_RESPONSE:"invalid-credential",INVALID_PENDING_TOKEN:"invalid-credential",FEDERATED_USER_ID_ALREADY_LINKED:"credential-already-in-use",MISSING_REQ_TYPE:"internal-error",EMAIL_NOT_FOUND:"user-not-found",RESET_PASSWORD_EXCEED_LIMIT:"too-many-requests",EXPIRED_OOB_CODE:"expired-action-code",INVALID_OOB_CODE:"invalid-action-code",MISSING_OOB_CODE:"internal-error",CREDENTIAL_TOO_OLD_LOGIN_AGAIN:"requires-recent-login",INVALID_ID_TOKEN:"invalid-user-token",TOKEN_EXPIRED:"user-token-expired",USER_NOT_FOUND:"user-token-expired",TOO_MANY_ATTEMPTS_TRY_LATER:"too-many-requests",PASSWORD_DOES_NOT_MEET_REQUIREMENTS:"password-does-not-meet-requirements",INVALID_CODE:"invalid-verification-code",INVALID_SESSION_INFO:"invalid-verification-id",INVALID_TEMPORARY_PROOF:"invalid-credential",MISSING_SESSION_INFO:"missing-verification-id",SESSION_EXPIRED:"code-expired",MISSING_ANDROID_PACKAGE_NAME:"missing-android-pkg-name",UNAUTHORIZED_DOMAIN:"unauthorized-continue-uri",INVALID_OAUTH_CLIENT_ID:"invalid-oauth-client-id",ADMIN_ONLY_OPERATION:"admin-restricted-operation",INVALID_MFA_PENDING_CREDENTIAL:"invalid-multi-factor-session",MFA_ENROLLMENT_NOT_FOUND:"multi-factor-info-not-found",MISSING_MFA_ENROLLMENT_ID:"missing-multi-factor-info",MISSING_MFA_PENDING_CREDENTIAL:"missing-multi-factor-session",SECOND_FACTOR_EXISTS:"second-factor-already-in-use",SECOND_FACTOR_LIMIT_EXCEEDED:"maximum-second-factor-count-exceeded",BLOCKING_FUNCTION_ERROR_RESPONSE:"internal-error",RECAPTCHA_NOT_ENABLED:"recaptcha-not-enabled",MISSING_RECAPTCHA_TOKEN:"missing-recaptcha-token",INVALID_RECAPTCHA_TOKEN:"invalid-recaptcha-token",INVALID_RECAPTCHA_ACTION:"invalid-recaptcha-action",MISSING_CLIENT_TYPE:"missing-client-type",MISSING_RECAPTCHA_VERSION:"missing-recaptcha-version",INVALID_RECAPTCHA_VERSION:"invalid-recaptcha-version",INVALID_REQ_TYPE:"invalid-req-type"};var Ps=new V(3e4,6e4);function p(t,e){return t.tenantId&&!e.tenantId?Object.assign(Object.assign({},e),{tenantId:t.tenantId}):e}async function g(t,e,n,r,i={}){return mr(t,i,async()=>{let s={},o={};r&&(e==="GET"?o=r:s={body:JSON.stringify(r)});let a=X(Object.assign({key:t.config.apiKey},o)).slice(1),c=await t._getAdditionalHeaders();c["Content-Type"]="application/json",t.languageCode&&(c["X-Firebase-Locale"]=t.languageCode);let u=Object.assign({method:e,headers:c},s);return Rn()||(u.referrerPolicy="no-referrer"),Le.fetch()(gr(t,t.config.apiHost,n,a),u)})}async function mr(t,e,n){t._canInitEmulator=!1;let r=Object.assign(Object.assign({},ks),e);try{let i=new Ut(t),s=await Promise.race([n(),i.promise]);i.clearNetworkTimeout();let o=await s.json();if("needConfirmation"in o)throw oe(t,"account-exists-with-different-credential",o);if(s.ok&&!("errorMessage"in o))return o;{let a=s.ok?o.errorMessage:o.error.message,[c,u]=a.split(" : ");if(c==="FEDERATED_USER_ID_ALREADY_LINKED")throw oe(t,"credential-already-in-use",o);if(c==="EMAIL_EXISTS")throw oe(t,"email-already-in-use",o);if(c==="USER_DISABLED")throw oe(t,"user-disabled",o);let d=r[c]||c.toLowerCase().replace(/[_\s]+/g,"-");if(u)throw pr(t,d,u);w(t,d)}}catch(i){if(i instanceof I)throw i;w(t,"network-request-failed",{message:String(i)})}}async function $(t,e,n,r,i={}){let s=await g(t,e,n,r,i);return"mfaPendingCredential"in s&&w(t,"multi-factor-auth-required",{_serverResponse:s}),s}function gr(t,e,n,r){let i=`${e}${n}?${r}`;return t.config.emulator?en(t.config,i):`${t.config.apiScheme}://${i}`}function Cs(t){switch(t){case"ENFORCE":return"ENFORCE";case"AUDIT":return"AUDIT";case"OFF":return"OFF";default:return"ENFORCEMENT_STATE_UNSPECIFIED"}}var Ut=class{constructor(e){this.auth=e,this.timer=null,this.promise=new Promise((n,r)=>{this.timer=setTimeout(()=>r(A(this.auth,"network-request-failed")),Ps.get())})}clearNetworkTimeout(){clearTimeout(this.timer)}};function oe(t,e,n){let r={appName:t.name};n.email&&(r.email=n.email),n.phoneNumber&&(r.phoneNumber=n.phoneNumber);let i=A(t,e,r);return i.customData._tokenResponse=n,i}function Jn(t){return t!==void 0&&t.enterprise!==void 0}var xt=class{constructor(e){if(this.siteKey="",this.recaptchaEnforcementState=[],e.recaptchaKey===void 0)throw new Error("recaptchaKey undefined");this.siteKey=e.recaptchaKey.split("/")[3],this.recaptchaEnforcementState=e.recaptchaEnforcementState}getProviderEnforcementState(e){if(!this.recaptchaEnforcementState||this.recaptchaEnforcementState.length===0)return null;for(let n of this.recaptchaEnforcementState)if(n.provider&&n.provider===e)return Cs(n.enforcementState);return null}isProviderEnabled(e){return this.getProviderEnforcementState(e)==="ENFORCE"||this.getProviderEnforcementState(e)==="AUDIT"}};async function Ns(t,e){return g(t,"GET","/v2/recaptchaConfig",p(t,e))}async function Ds(t,e){return g(t,"POST","/v1/accounts:delete",e)}async function _r(t,e){return g(t,"POST","/v1/accounts:lookup",e)}function ae(t){if(t)try{let e=new Date(Number(t));if(!isNaN(e.getTime()))return e.toUTCString()}catch{}}function tn(t,e=!1){return O(t).getIdToken(e)}async function Ir(t,e=!1){let n=O(t),r=await n.getIdToken(e),i=nn(r);l(i&&i.exp&&i.auth_time&&i.iat,n.auth,"internal-error");let s=typeof i.firebase=="object"?i.firebase:void 0,o=s?.sign_in_provider;return{claims:i,token:r,authTime:ae(Dt(i.auth_time)),issuedAtTime:ae(Dt(i.iat)),expirationTime:ae(Dt(i.exp)),signInProvider:o||null,signInSecondFactor:s?.sign_in_second_factor||null}}function Dt(t){return Number(t)*1e3}function nn(t){let[e,n,r]=t.split(".");if(e===void 0||n===void 0||r===void 0)return ke("JWT malformed, contained fewer than 3 sections"),null;try{let i=pt(n);return i?JSON.parse(i):(ke("Failed to decode base64 JWT payload"),null)}catch(i){return ke("Caught error parsing JWT payload as JSON",i?.toString()),null}}function Yn(t){let e=nn(t);return l(e,"internal-error"),l(typeof e.exp<"u","internal-error"),l(typeof e.iat<"u","internal-error"),Number(e.exp)-Number(e.iat)}async function ue(t,e,n=!1){if(n)return e;try{return await e}catch(r){throw r instanceof I&&Ls(r)&&t.auth.currentUser===t&&await t.auth.signOut(),r}}function Ls({code:t}){return t==="auth/user-disabled"||t==="auth/user-token-expired"}var Ft=class{constructor(e){this.user=e,this.isRunning=!1,this.timerId=null,this.errorBackoff=3e4}_start(){this.isRunning||(this.isRunning=!0,this.schedule())}_stop(){this.isRunning&&(this.isRunning=!1,this.timerId!==null&&clearTimeout(this.timerId))}getInterval(e){var n;if(e){let r=this.errorBackoff;return this.errorBackoff=Math.min(this.errorBackoff*2,96e4),r}else{this.errorBackoff=3e4;let i=((n=this.user.stsTokenManager.expirationTime)!==null&&n!==void 0?n:0)-Date.now()-3e5;return Math.max(0,i)}}schedule(e=!1){if(!this.isRunning)return;let n=this.getInterval(e);this.timerId=setTimeout(async()=>{await this.iteration()},n)}async iteration(){try{await this.user.getIdToken(!0)}catch(e){e?.code==="auth/network-request-failed"&&this.schedule(!0);return}this.schedule()}};var le=class{constructor(e,n){this.createdAt=e,this.lastLoginAt=n,this._initializeTime()}_initializeTime(){this.lastSignInTime=ae(this.lastLoginAt),this.creationTime=ae(this.createdAt)}_copy(e){this.createdAt=e.createdAt,this.lastLoginAt=e.lastLoginAt,this._initializeTime()}toJSON(){return{createdAt:this.createdAt,lastLoginAt:this.lastLoginAt}}};async function Me(t){var e;let n=t.auth,r=await t.getIdToken(),i=await ue(t,_r(n,{idToken:r}));l(i?.users.length,n,"internal-error");let s=i.users[0];t._notifyReloadListener(s);let o=!((e=s.providerUserInfo)===null||e===void 0)&&e.length?yr(s.providerUserInfo):[],a=Ms(t.providerData,o),c=t.isAnonymous,u=!(t.email&&s.passwordHash)&&!a?.length,d=c?u:!1,f={uid:s.localId,displayName:s.displayName||null,photoURL:s.photoUrl||null,email:s.email||null,emailVerified:s.emailVerified||!1,phoneNumber:s.phoneNumber||null,tenantId:s.tenantId||null,providerData:a,metadata:new le(s.createdAt,s.lastLoginAt),isAnonymous:d};Object.assign(t,f)}async function vr(t){let e=O(t);await Me(e),await e.auth._persistUserIfCurrent(e),e.auth._notifyListenersIfCurrent(e)}function Ms(t,e){return[...t.filter(r=>!e.some(i=>i.providerId===r.providerId)),...e]}function yr(t){return t.map(e=>{var{providerId:n}=e,r=Re(e,["providerId"]);return{providerId:n,uid:r.rawId||"",displayName:r.displayName||null,email:r.email||null,phoneNumber:r.phoneNumber||null,photoURL:r.photoUrl||null}})}async function Us(t,e){let n=await mr(t,{},async()=>{let r=X({grant_type:"refresh_token",refresh_token:e}).slice(1),{tokenApiHost:i,apiKey:s}=t.config,o=gr(t,i,"/v1/token",`key=${s}`),a=await t._getAdditionalHeaders();return a["Content-Type"]="application/x-www-form-urlencoded",Le.fetch()(o,{method:"POST",headers:a,body:r})});return{accessToken:n.access_token,expiresIn:n.expires_in,refreshToken:n.refresh_token}}async function xs(t,e){return g(t,"POST","/v2/accounts:revokeToken",p(t,e))}var ce=class t{constructor(){this.refreshToken=null,this.accessToken=null,this.expirationTime=null}get isExpired(){return!this.expirationTime||Date.now()>this.expirationTime-3e4}updateFromServerResponse(e){l(e.idToken,"internal-error"),l(typeof e.idToken<"u","internal-error"),l(typeof e.refreshToken<"u","internal-error");let n="expiresIn"in e&&typeof e.expiresIn<"u"?Number(e.expiresIn):Yn(e.idToken);this.updateTokensAndExpiration(e.idToken,e.refreshToken,n)}updateFromIdToken(e){l(e.length!==0,"internal-error");let n=Yn(e);this.updateTokensAndExpiration(e,null,n)}async getToken(e,n=!1){return!n&&this.accessToken&&!this.isExpired?this.accessToken:(l(this.refreshToken,e,"user-token-expired"),this.refreshToken?(await this.refresh(e,this.refreshToken),this.accessToken):null)}clearRefreshToken(){this.refreshToken=null}async refresh(e,n){let{accessToken:r,refreshToken:i,expiresIn:s}=await Us(e,n);this.updateTokensAndExpiration(r,i,Number(s))}updateTokensAndExpiration(e,n,r){this.refreshToken=n||null,this.accessToken=e||null,this.expirationTime=Date.now()+r*1e3}static fromJSON(e,n){let{refreshToken:r,accessToken:i,expirationTime:s}=n,o=new t;return r&&(l(typeof r=="string","internal-error",{appName:e}),o.refreshToken=r),i&&(l(typeof i=="string","internal-error",{appName:e}),o.accessToken=i),s&&(l(typeof s=="number","internal-error",{appName:e}),o.expirationTime=s),o}toJSON(){return{refreshToken:this.refreshToken,accessToken:this.accessToken,expirationTime:this.expirationTime}}_assign(e){this.accessToken=e.accessToken,this.refreshToken=e.refreshToken,this.expirationTime=e.expirationTime}_clone(){return Object.assign(new t,this.toJSON())}_performRefresh(){return b("not implemented")}};function M(t,e){l(typeof t=="string"||typeof t>"u","internal-error",{appName:e})}var re=class t{constructor(e){var{uid:n,auth:r,stsTokenManager:i}=e,s=Re(e,["uid","auth","stsTokenManager"]);this.providerId="firebase",this.proactiveRefresh=new Ft(this),this.reloadUserInfo=null,this.reloadListener=null,this.uid=n,this.auth=r,this.stsTokenManager=i,this.accessToken=i.accessToken,this.displayName=s.displayName||null,this.email=s.email||null,this.emailVerified=s.emailVerified||!1,this.phoneNumber=s.phoneNumber||null,this.photoURL=s.photoURL||null,this.isAnonymous=s.isAnonymous||!1,this.tenantId=s.tenantId||null,this.providerData=s.providerData?[...s.providerData]:[],this.metadata=new le(s.createdAt||void 0,s.lastLoginAt||void 0)}async getIdToken(e){let n=await ue(this,this.stsTokenManager.getToken(this.auth,e));return l(n,this.auth,"internal-error"),this.accessToken!==n&&(this.accessToken=n,await this.auth._persistUserIfCurrent(this),this.auth._notifyListenersIfCurrent(this)),n}getIdTokenResult(e){return Ir(this,e)}reload(){return vr(this)}_assign(e){this!==e&&(l(this.uid===e.uid,this.auth,"internal-error"),this.displayName=e.displayName,this.photoURL=e.photoURL,this.email=e.email,this.emailVerified=e.emailVerified,this.phoneNumber=e.phoneNumber,this.isAnonymous=e.isAnonymous,this.tenantId=e.tenantId,this.providerData=e.providerData.map(n=>Object.assign({},n)),this.metadata._copy(e.metadata),this.stsTokenManager._assign(e.stsTokenManager))}_clone(e){let n=new t(Object.assign(Object.assign({},this),{auth:e,stsTokenManager:this.stsTokenManager._clone()}));return n.metadata._copy(this.metadata),n}_onReload(e){l(!this.reloadListener,this.auth,"internal-error"),this.reloadListener=e,this.reloadUserInfo&&(this._notifyReloadListener(this.reloadUserInfo),this.reloadUserInfo=null)}_notifyReloadListener(e){this.reloadListener?this.reloadListener(e):this.reloadUserInfo=e}_startProactiveRefresh(){this.proactiveRefresh._start()}_stopProactiveRefresh(){this.proactiveRefresh._stop()}async _updateTokensIfNecessary(e,n=!1){let r=!1;e.idToken&&e.idToken!==this.stsTokenManager.accessToken&&(this.stsTokenManager.updateFromServerResponse(e),r=!0),n&&await Me(this),await this.auth._persistUserIfCurrent(this),r&&this.auth._notifyListenersIfCurrent(this)}async delete(){if(C(this.auth.app))return Promise.reject(F(this.auth));let e=await this.getIdToken();return await ue(this,Ds(this.auth,{idToken:e})),this.stsTokenManager.clearRefreshToken(),this.auth.signOut()}toJSON(){return Object.assign(Object.assign({uid:this.uid,email:this.email||void 0,emailVerified:this.emailVerified,displayName:this.displayName||void 0,isAnonymous:this.isAnonymous,photoURL:this.photoURL||void 0,phoneNumber:this.phoneNumber||void 0,tenantId:this.tenantId||void 0,providerData:this.providerData.map(e=>Object.assign({},e)),stsTokenManager:this.stsTokenManager.toJSON(),_redirectEventId:this._redirectEventId},this.metadata.toJSON()),{apiKey:this.auth.config.apiKey,appName:this.auth.name})}get refreshToken(){return this.stsTokenManager.refreshToken||""}static _fromJSON(e,n){var r,i,s,o,a,c,u,d;let f=(r=n.displayName)!==null&&r!==void 0?r:void 0,_=(i=n.email)!==null&&i!==void 0?i:void 0,R=(s=n.phoneNumber)!==null&&s!==void 0?s:void 0,J=(o=n.photoURL)!==null&&o!==void 0?o:void 0,gn=(a=n.tenantId)!==null&&a!==void 0?a:void 0,ot=(c=n._redirectEventId)!==null&&c!==void 0?c:void 0,_n=(u=n.createdAt)!==null&&u!==void 0?u:void 0,In=(d=n.lastLoginAt)!==null&&d!==void 0?d:void 0,{uid:at,emailVerified:vn,isAnonymous:yn,providerData:ct,stsTokenManager:En}=n;l(at&&En,e,"internal-error");let hi=ce.fromJSON(this.name,En);l(typeof at=="string",e,"internal-error"),M(f,e.name),M(_,e.name),l(typeof vn=="boolean",e,"internal-error"),l(typeof yn=="boolean",e,"internal-error"),M(R,e.name),M(J,e.name),M(gn,e.name),M(ot,e.name),M(_n,e.name),M(In,e.name);let ut=new t({uid:at,auth:e,email:_,emailVerified:vn,displayName:f,isAnonymous:yn,photoURL:J,phoneNumber:R,tenantId:gn,stsTokenManager:hi,createdAt:_n,lastLoginAt:In});return ct&&Array.isArray(ct)&&(ut.providerData=ct.map(fi=>Object.assign({},fi))),ot&&(ut._redirectEventId=ot),ut}static async _fromIdTokenResponse(e,n,r=!1){let i=new ce;i.updateFromServerResponse(n);let s=new t({uid:n.localId,auth:e,stsTokenManager:i,isAnonymous:r});return await Me(s),s}static async _fromGetAccountInfoResponse(e,n,r){let i=n.users[0];l(i.localId!==void 0,"internal-error");let s=i.providerUserInfo!==void 0?yr(i.providerUserInfo):[],o=!(i.email&&i.passwordHash)&&!s?.length,a=new ce;a.updateFromIdToken(r);let c=new t({uid:i.localId,auth:e,stsTokenManager:a,isAnonymous:o}),u={uid:i.localId,displayName:i.displayName||null,photoURL:i.photoUrl||null,email:i.email||null,emailVerified:i.emailVerified||!1,phoneNumber:i.phoneNumber||null,tenantId:i.tenantId||null,providerData:s,metadata:new le(i.createdAt,i.lastLoginAt),isAnonymous:!(i.email&&i.passwordHash)&&!s?.length};return Object.assign(c,u),c}};var Xn=new Map;function N(t){D(t instanceof Function,"Expected a class definition");let e=Xn.get(t);return e?(D(e instanceof t,"Instance stored in cache mismatched with class"),e):(e=new t,Xn.set(t,e),e)}var Ue=class{constructor(){this.type="NONE",this.storage={}}async _isAvailable(){return!0}async _set(e,n){this.storage[e]=n}async _get(e){let n=this.storage[e];return n===void 0?null:n}async _remove(e){delete this.storage[e]}_addListener(e,n){}_removeListener(e,n){}};Ue.type="NONE";var Vt=Ue;function Pe(t,e,n){return`firebase:${t}:${e}:${n}`}var xe=class t{constructor(e,n,r){this.persistence=e,this.auth=n,this.userKey=r;let{config:i,name:s}=this.auth;this.fullUserKey=Pe(this.userKey,i.apiKey,s),this.fullPersistenceKey=Pe("persistence",i.apiKey,s),this.boundEventHandler=n._onStorageEvent.bind(n),this.persistence._addListener(this.fullUserKey,this.boundEventHandler)}setCurrentUser(e){return this.persistence._set(this.fullUserKey,e.toJSON())}async getCurrentUser(){let e=await this.persistence._get(this.fullUserKey);return e?re._fromJSON(this.auth,e):null}removeCurrentUser(){return this.persistence._remove(this.fullUserKey)}savePersistenceForRedirect(){return this.persistence._set(this.fullPersistenceKey,this.persistence.type)}async setPersistence(e){if(this.persistence===e)return;let n=await this.getCurrentUser();if(await this.removeCurrentUser(),this.persistence=e,n)return this.setCurrentUser(n)}delete(){this.persistence._removeListener(this.fullUserKey,this.boundEventHandler)}static async create(e,n,r="authUser"){if(!n.length)return new t(N(Vt),e,r);let i=(await Promise.all(n.map(async u=>{if(await u._isAvailable())return u}))).filter(u=>u),s=i[0]||N(Vt),o=Pe(r,e.config.apiKey,e.name),a=null;for(let u of n)try{let d=await u._get(o);if(d){let f=re._fromJSON(e,d);u!==s&&(a=f),s=u;break}}catch{}let c=i.filter(u=>u._shouldAllowMigration);return!s._shouldAllowMigration||!c.length?new t(s,e,r):(s=c[0],a&&await s._set(o,a.toJSON()),await Promise.all(n.map(async u=>{if(u!==s)try{await u._remove(o)}catch{}})),new t(s,e,r))}};function Qn(t){let e=t.toLowerCase();if(e.includes("opera/")||e.includes("opr/")||e.includes("opios/"))return"Opera";if(br(e))return"IEMobile";if(e.includes("msie")||e.includes("trident/"))return"IE";if(e.includes("edge/"))return"Edge";if(Er(e))return"Firefox";if(e.includes("silk/"))return"Silk";if(Sr(e))return"Blackberry";if(Rr(e))return"Webos";if(wr(e))return"Safari";if((e.includes("chrome/")||Tr(e))&&!e.includes("edge/"))return"Chrome";if(Ar(e))return"Android";{let n=/([a-zA-Z\d\.]+)\/[a-zA-Z\d\.]*$/,r=t.match(n);if(r?.length===2)return r[1]}return"Other"}function Er(t=m()){return/firefox\//i.test(t)}function wr(t=m()){let e=t.toLowerCase();return e.includes("safari/")&&!e.includes("chrome/")&&!e.includes("crios/")&&!e.includes("android")}function Tr(t=m()){return/crios\//i.test(t)}function br(t=m()){return/iemobile/i.test(t)}function Ar(t=m()){return/android/i.test(t)}function Sr(t=m()){return/blackberry/i.test(t)}function Rr(t=m()){return/webos/i.test(t)}function rn(t=m()){return/iphone|ipad|ipod/i.test(t)||/macintosh/i.test(t)&&/mobile/i.test(t)}function Fs(t=m()){var e;return rn(t)&&!!(!((e=window.navigator)===null||e===void 0)&&e.standalone)}function Vs(){return Pn()&&document.documentMode===10}function Or(t=m()){return rn(t)||Ar(t)||Rr(t)||Sr(t)||/windows phone/i.test(t)||br(t)}function kr(t,e=[]){let n;switch(t){case"Browser":n=Qn(m());break;case"Worker":n=`${Qn(m())}-${t}`;break;default:n=t}let r=e.length?e.join(","):"FirebaseCore-web";return`${n}/JsCore/${te}/${r}`}var jt=class{constructor(e){this.auth=e,this.queue=[]}pushCallback(e,n){let r=s=>new Promise((o,a)=>{try{let c=e(s);o(c)}catch(c){a(c)}});r.onAbort=n,this.queue.push(r);let i=this.queue.length-1;return()=>{this.queue[i]=()=>Promise.resolve()}}async runMiddleware(e){if(this.auth.currentUser===e)return;let n=[];try{for(let r of this.queue)await r(e),r.onAbort&&n.push(r.onAbort)}catch(r){n.reverse();for(let i of n)try{i()}catch{}throw this.auth._errorFactory.create("login-blocked",{originalMessage:r?.message})}}};async function js(t,e={}){return g(t,"GET","/v2/passwordPolicy",p(t,e))}var Hs=6,Ht=class{constructor(e){var n,r,i,s;let o=e.customStrengthOptions;this.customStrengthOptions={},this.customStrengthOptions.minPasswordLength=(n=o.minPasswordLength)!==null&&n!==void 0?n:Hs,o.maxPasswordLength&&(this.customStrengthOptions.maxPasswordLength=o.maxPasswordLength),o.containsLowercaseCharacter!==void 0&&(this.customStrengthOptions.containsLowercaseLetter=o.containsLowercaseCharacter),o.containsUppercaseCharacter!==void 0&&(this.customStrengthOptions.containsUppercaseLetter=o.containsUppercaseCharacter),o.containsNumericCharacter!==void 0&&(this.customStrengthOptions.containsNumericCharacter=o.containsNumericCharacter),o.containsNonAlphanumericCharacter!==void 0&&(this.customStrengthOptions.containsNonAlphanumericCharacter=o.containsNonAlphanumericCharacter),this.enforcementState=e.enforcementState,this.enforcementState==="ENFORCEMENT_STATE_UNSPECIFIED"&&(this.enforcementState="OFF"),this.allowedNonAlphanumericCharacters=(i=(r=e.allowedNonAlphanumericCharacters)===null||r===void 0?void 0:r.join(""))!==null&&i!==void 0?i:"",this.forceUpgradeOnSignin=(s=e.forceUpgradeOnSignin)!==null&&s!==void 0?s:!1,this.schemaVersion=e.schemaVersion}validatePassword(e){var n,r,i,s,o,a;let c={isValid:!0,passwordPolicy:this};return this.validatePasswordLengthOptions(e,c),this.validatePasswordCharacterOptions(e,c),c.isValid&&(c.isValid=(n=c.meetsMinPasswordLength)!==null&&n!==void 0?n:!0),c.isValid&&(c.isValid=(r=c.meetsMaxPasswordLength)!==null&&r!==void 0?r:!0),c.isValid&&(c.isValid=(i=c.containsLowercaseLetter)!==null&&i!==void 0?i:!0),c.isValid&&(c.isValid=(s=c.containsUppercaseLetter)!==null&&s!==void 0?s:!0),c.isValid&&(c.isValid=(o=c.containsNumericCharacter)!==null&&o!==void 0?o:!0),c.isValid&&(c.isValid=(a=c.containsNonAlphanumericCharacter)!==null&&a!==void 0?a:!0),c}validatePasswordLengthOptions(e,n){let r=this.customStrengthOptions.minPasswordLength,i=this.customStrengthOptions.maxPasswordLength;r&&(n.meetsMinPasswordLength=e.length>=r),i&&(n.meetsMaxPasswordLength=e.length<=i)}validatePasswordCharacterOptions(e,n){this.updatePasswordCharacterOptionsStatuses(n,!1,!1,!1,!1);let r;for(let i=0;i<e.length;i++)r=e.charAt(i),this.updatePasswordCharacterOptionsStatuses(n,r>="a"&&r<="z",r>="A"&&r<="Z",r>="0"&&r<="9",this.allowedNonAlphanumericCharacters.includes(r))}updatePasswordCharacterOptionsStatuses(e,n,r,i,s){this.customStrengthOptions.containsLowercaseLetter&&(e.containsLowercaseLetter||(e.containsLowercaseLetter=n)),this.customStrengthOptions.containsUppercaseLetter&&(e.containsUppercaseLetter||(e.containsUppercaseLetter=r)),this.customStrengthOptions.containsNumericCharacter&&(e.containsNumericCharacter||(e.containsNumericCharacter=i)),this.customStrengthOptions.containsNonAlphanumericCharacter&&(e.containsNonAlphanumericCharacter||(e.containsNonAlphanumericCharacter=s))}};var Wt=class{constructor(e,n,r,i){this.app=e,this.heartbeatServiceProvider=n,this.appCheckServiceProvider=r,this.config=i,this.currentUser=null,this.emulatorConfig=null,this.operations=Promise.resolve(),this.authStateSubscription=new Fe(this),this.idTokenSubscription=new Fe(this),this.beforeStateQueue=new jt(this),this.redirectUser=null,this.isProactiveRefreshEnabled=!1,this.EXPECTED_PASSWORD_POLICY_SCHEMA_VERSION=1,this._canInitEmulator=!0,this._isInitialized=!1,this._deleted=!1,this._initializationPromise=null,this._popupRedirectResolver=null,this._errorFactory=fr,this._agentRecaptchaConfig=null,this._tenantRecaptchaConfigs={},this._projectPasswordPolicy=null,this._tenantPasswordPolicies={},this.lastNotifiedUid=void 0,this.languageCode=null,this.tenantId=null,this.settings={appVerificationDisabledForTesting:!1},this.frameworks=[],this.name=e.name,this.clientVersion=i.sdkClientVersion}_initializeWithPersistence(e,n){return n&&(this._popupRedirectResolver=N(n)),this._initializationPromise=this.queue(async()=>{var r,i;if(!this._deleted&&(this.persistenceManager=await xe.create(this,e),!this._deleted)){if(!((r=this._popupRedirectResolver)===null||r===void 0)&&r._shouldInitProactively)try{await this._popupRedirectResolver._initialize(this)}catch{}await this.initializeCurrentUser(n),this.lastNotifiedUid=((i=this.currentUser)===null||i===void 0?void 0:i.uid)||null,!this._deleted&&(this._isInitialized=!0)}}),this._initializationPromise}async _onStorageEvent(){if(this._deleted)return;let e=await this.assertedPersistence.getCurrentUser();if(!(!this.currentUser&&!e)){if(this.currentUser&&e&&this.currentUser.uid===e.uid){this._currentUser._assign(e),await this.currentUser.getIdToken();return}await this._updateCurrentUser(e,!0)}}async initializeCurrentUserFromIdToken(e){try{let n=await _r(this,{idToken:e}),r=await re._fromGetAccountInfoResponse(this,n,e);await this.directlySetCurrentUser(r)}catch(n){console.warn("FirebaseServerApp could not login user with provided authIdToken: ",n),await this.directlySetCurrentUser(null)}}async initializeCurrentUser(e){var n;if(C(this.app)){let o=this.app.settings.authIdToken;return o?new Promise(a=>{setTimeout(()=>this.initializeCurrentUserFromIdToken(o).then(a,a))}):this.directlySetCurrentUser(null)}let r=await this.assertedPersistence.getCurrentUser(),i=r,s=!1;if(e&&this.config.authDomain){await this.getOrInitRedirectPersistenceManager();let o=(n=this.redirectUser)===null||n===void 0?void 0:n._redirectEventId,a=i?._redirectEventId,c=await this.tryRedirectSignIn(e);(!o||o===a)&&c?.user&&(i=c.user,s=!0)}if(!i)return this.directlySetCurrentUser(null);if(!i._redirectEventId){if(s)try{await this.beforeStateQueue.runMiddleware(i)}catch(o){i=r,this._popupRedirectResolver._overrideRedirectResult(this,()=>Promise.reject(o))}return i?this.reloadAndSetCurrentUserOrClear(i):this.directlySetCurrentUser(null)}return l(this._popupRedirectResolver,this,"argument-error"),await this.getOrInitRedirectPersistenceManager(),this.redirectUser&&this.redirectUser._redirectEventId===i._redirectEventId?this.directlySetCurrentUser(i):this.reloadAndSetCurrentUserOrClear(i)}async tryRedirectSignIn(e){let n=null;try{n=await this._popupRedirectResolver._completeRedirectFn(this,e,!0)}catch{await this._setRedirectUser(null)}return n}async reloadAndSetCurrentUserOrClear(e){try{await Me(e)}catch(n){if(n?.code!=="auth/network-request-failed")return this.directlySetCurrentUser(null)}return this.directlySetCurrentUser(e)}useDeviceLanguage(){this.languageCode=Os()}async _delete(){this._deleted=!0}async updateCurrentUser(e){if(C(this.app))return Promise.reject(F(this));let n=e?O(e):null;return n&&l(n.auth.config.apiKey===this.config.apiKey,this,"invalid-user-token"),this._updateCurrentUser(n&&n._clone(this))}async _updateCurrentUser(e,n=!1){if(!this._deleted)return e&&l(this.tenantId===e.tenantId,this,"tenant-id-mismatch"),n||await this.beforeStateQueue.runMiddleware(e),this.queue(async()=>{await this.directlySetCurrentUser(e),this.notifyAuthListeners()})}async signOut(){return C(this.app)?Promise.reject(F(this)):(await this.beforeStateQueue.runMiddleware(null),(this.redirectPersistenceManager||this._popupRedirectResolver)&&await this._setRedirectUser(null),this._updateCurrentUser(null,!0))}setPersistence(e){return C(this.app)?Promise.reject(F(this)):this.queue(async()=>{await this.assertedPersistence.setPersistence(N(e))})}_getRecaptchaConfig(){return this.tenantId==null?this._agentRecaptchaConfig:this._tenantRecaptchaConfigs[this.tenantId]}async validatePassword(e){this._getPasswordPolicyInternal()||await this._updatePasswordPolicy();let n=this._getPasswordPolicyInternal();return n.schemaVersion!==this.EXPECTED_PASSWORD_POLICY_SCHEMA_VERSION?Promise.reject(this._errorFactory.create("unsupported-password-policy-schema-version",{})):n.validatePassword(e)}_getPasswordPolicyInternal(){return this.tenantId===null?this._projectPasswordPolicy:this._tenantPasswordPolicies[this.tenantId]}async _updatePasswordPolicy(){let e=await js(this),n=new Ht(e);this.tenantId===null?this._projectPasswordPolicy=n:this._tenantPasswordPolicies[this.tenantId]=n}_getPersistence(){return this.assertedPersistence.persistence.type}_updateErrorMap(e){this._errorFactory=new y("auth","Firebase",e())}onAuthStateChanged(e,n,r){return this.registerStateListener(this.authStateSubscription,e,n,r)}beforeAuthStateChanged(e,n){return this.beforeStateQueue.pushCallback(e,n)}onIdTokenChanged(e,n,r){return this.registerStateListener(this.idTokenSubscription,e,n,r)}authStateReady(){return new Promise((e,n)=>{if(this.currentUser)e();else{let r=this.onAuthStateChanged(()=>{r(),e()},n)}})}async revokeAccessToken(e){if(this.currentUser){let n=await this.currentUser.getIdToken(),r={providerId:"apple.com",tokenType:"ACCESS_TOKEN",token:e,idToken:n};this.tenantId!=null&&(r.tenantId=this.tenantId),await xs(this,r)}}toJSON(){var e;return{apiKey:this.config.apiKey,authDomain:this.config.authDomain,appName:this.name,currentUser:(e=this._currentUser)===null||e===void 0?void 0:e.toJSON()}}async _setRedirectUser(e,n){let r=await this.getOrInitRedirectPersistenceManager(n);return e===null?r.removeCurrentUser():r.setCurrentUser(e)}async getOrInitRedirectPersistenceManager(e){if(!this.redirectPersistenceManager){let n=e&&N(e)||this._popupRedirectResolver;l(n,this,"argument-error"),this.redirectPersistenceManager=await xe.create(this,[N(n._redirectPersistence)],"redirectUser"),this.redirectUser=await this.redirectPersistenceManager.getCurrentUser()}return this.redirectPersistenceManager}async _redirectUserForId(e){var n,r;return this._isInitialized&&await this.queue(async()=>{}),((n=this._currentUser)===null||n===void 0?void 0:n._redirectEventId)===e?this._currentUser:((r=this.redirectUser)===null||r===void 0?void 0:r._redirectEventId)===e?this.redirectUser:null}async _persistUserIfCurrent(e){if(e===this.currentUser)return this.queue(async()=>this.directlySetCurrentUser(e))}_notifyListenersIfCurrent(e){e===this.currentUser&&this.notifyAuthListeners()}_key(){return`${this.config.authDomain}:${this.config.apiKey}:${this.name}`}_startProactiveRefresh(){this.isProactiveRefreshEnabled=!0,this.currentUser&&this._currentUser._startProactiveRefresh()}_stopProactiveRefresh(){this.isProactiveRefreshEnabled=!1,this.currentUser&&this._currentUser._stopProactiveRefresh()}get _currentUser(){return this.currentUser}notifyAuthListeners(){var e,n;if(!this._isInitialized)return;this.idTokenSubscription.next(this.currentUser);let r=(n=(e=this.currentUser)===null||e===void 0?void 0:e.uid)!==null&&n!==void 0?n:null;this.lastNotifiedUid!==r&&(this.lastNotifiedUid=r,this.authStateSubscription.next(this.currentUser))}registerStateListener(e,n,r,i){if(this._deleted)return()=>{};let s=typeof n=="function"?n:n.next.bind(n),o=!1,a=this._isInitialized?Promise.resolve():this._initializationPromise;if(l(a,this,"internal-error"),a.then(()=>{o||s(this.currentUser)}),typeof n=="function"){let c=e.addObserver(n,r,i);return()=>{o=!0,c()}}else{let c=e.addObserver(n);return()=>{o=!0,c()}}}async directlySetCurrentUser(e){this.currentUser&&this.currentUser!==e&&this._currentUser._stopProactiveRefresh(),e&&this.isProactiveRefreshEnabled&&e._startProactiveRefresh(),this.currentUser=e,e?await this.assertedPersistence.setCurrentUser(e):await this.assertedPersistence.removeCurrentUser()}queue(e){return this.operations=this.operations.then(e,e),this.operations}get assertedPersistence(){return l(this.persistenceManager,this,"internal-error"),this.persistenceManager}_logFramework(e){!e||this.frameworks.includes(e)||(this.frameworks.push(e),this.frameworks.sort(),this.clientVersion=kr(this.config.clientPlatform,this._getFrameworks()))}_getFrameworks(){return this.frameworks}async _getAdditionalHeaders(){var e;let n={"X-Client-Version":this.clientVersion};this.app.options.appId&&(n["X-Firebase-gmpid"]=this.app.options.appId);let r=await((e=this.heartbeatServiceProvider.getImmediate({optional:!0}))===null||e===void 0?void 0:e.getHeartbeatsHeader());r&&(n["X-Firebase-Client"]=r);let i=await this._getAppCheckToken();return i&&(n["X-Firebase-AppCheck"]=i),n}async _getAppCheckToken(){var e;let n=await((e=this.appCheckServiceProvider.getImmediate({optional:!0}))===null||e===void 0?void 0:e.getToken());return n?.error&&As(`Error while retrieving App Check token: ${n.error}`),n?.token}};function ye(t){return O(t)}var Fe=class{constructor(e){this.auth=e,this.observer=null,this.addObserver=Ln(n=>this.observer=n)}get next(){return l(this.observer,this.auth,"internal-error"),this.observer.next.bind(this.observer)}};var tt={async loadJS(){throw new Error("Unable to load external scripts")},recaptchaV2Script:"",recaptchaEnterpriseScript:"",gapiScript:""};function Ws(t){tt=t}function Pr(t){return tt.loadJS(t)}function Bs(){return tt.recaptchaEnterpriseScript}function $s(){return tt.gapiScript}function Cr(t){return`__${t}${Math.floor(Math.random()*1e6)}`}var qs="recaptcha-enterprise",zs="NO_RECAPTCHA",Bt=class{constructor(e){this.type=qs,this.auth=ye(e)}async verify(e="verify",n=!1){async function r(s){if(!n){if(s.tenantId==null&&s._agentRecaptchaConfig!=null)return s._agentRecaptchaConfig.siteKey;if(s.tenantId!=null&&s._tenantRecaptchaConfigs[s.tenantId]!==void 0)return s._tenantRecaptchaConfigs[s.tenantId].siteKey}return new Promise(async(o,a)=>{Ns(s,{clientType:"CLIENT_TYPE_WEB",version:"RECAPTCHA_ENTERPRISE"}).then(c=>{if(c.recaptchaKey===void 0)a(new Error("recaptcha Enterprise site key undefined"));else{let u=new xt(c);return s.tenantId==null?s._agentRecaptchaConfig=u:s._tenantRecaptchaConfigs[s.tenantId]=u,o(u.siteKey)}}).catch(c=>{a(c)})})}function i(s,o,a){let c=window.grecaptcha;Jn(c)?c.enterprise.ready(()=>{c.enterprise.execute(s,{action:e}).then(u=>{o(u)}).catch(()=>{o(zs)})}):a(Error("No reCAPTCHA enterprise script loaded."))}return new Promise((s,o)=>{r(this.auth).then(a=>{if(!n&&Jn(window.grecaptcha))i(a,s,o);else{if(typeof window>"u"){o(new Error("RecaptchaVerifier is only supported in browser"));return}let c=Bs();c.length!==0&&(c+=a),Pr(c).then(()=>{i(a,s,o)}).catch(u=>{o(u)})}}).catch(a=>{o(a)})})}};async function Zn(t,e,n,r=!1){let i=new Bt(t),s;try{s=await i.verify(n)}catch{s=await i.verify(n,!0)}let o=Object.assign({},e);return r?Object.assign(o,{captchaResp:s}):Object.assign(o,{captchaResponse:s}),Object.assign(o,{clientType:"CLIENT_TYPE_WEB"}),Object.assign(o,{recaptchaVersion:"RECAPTCHA_ENTERPRISE"}),o}async function er(t,e,n,r){var i;if(!((i=t._getRecaptchaConfig())===null||i===void 0)&&i.isProviderEnabled("EMAIL_PASSWORD_PROVIDER")){let s=await Zn(t,e,n,n==="getOobCode");return r(t,s)}else return r(t,e).catch(async s=>{if(s.code==="auth/missing-recaptcha-token"){console.log(`${n} is protected by reCAPTCHA Enterprise for this project. Automatically triggering the reCAPTCHA flow and restarting the flow.`);let o=await Zn(t,e,n,n==="getOobCode");return r(t,o)}else return Promise.reject(s)})}function Nr(t,e){let n=x(t,"auth");if(n.isInitialized()){let i=n.getImmediate(),s=n.getOptions();if(Y(s,e??{}))return i;w(i,"already-initialized")}return n.initialize({options:e})}function Gs(t,e){let n=e?.persistence||[],r=(Array.isArray(n)?n:[n]).map(N);e?.errorMap&&t._updateErrorMap(e.errorMap),t._initializeWithPersistence(r,e?.popupRedirectResolver)}function Dr(t,e,n){let r=ye(t);l(r._canInitEmulator,r,"emulator-config-failed"),l(/^https?:\/\//.test(e),r,"invalid-emulator-scheme");let i=!!n?.disableWarnings,s=Lr(e),{host:o,port:a}=Ks(e),c=a===null?"":`:${a}`;r.config.emulator={url:`${s}//${o}${c}/`},r.settings.appVerificationDisabledForTesting=!0,r.emulatorConfig=Object.freeze({host:o,port:a,protocol:s.replace(":",""),options:Object.freeze({disableWarnings:i})}),i||Js()}function Lr(t){let e=t.indexOf(":");return e<0?"":t.substr(0,e+1)}function Ks(t){let e=Lr(t),n=/(\/\/)?([^?#/]+)/.exec(t.substr(e.length));if(!n)return{host:"",port:null};let r=n[2].split("@").pop()||"",i=/^(\[[^\]]+\])(:|$)/.exec(r);if(i){let s=i[1];return{host:s,port:tr(r.substr(s.length+1))}}else{let[s,o]=r.split(":");return{host:s,port:tr(o)}}}function tr(t){if(!t)return null;let e=Number(t);return isNaN(e)?null:e}function Js(){function t(){let e=document.createElement("p"),n=e.style;e.innerText="Running in emulator mode. Do not use with production credentials.",n.position="fixed",n.width="100%",n.backgroundColor="#ffffff",n.border=".1em solid #000000",n.color="#b50000",n.bottom="0px",n.left="0px",n.margin="0px",n.zIndex="10000",n.textAlign="center",e.classList.add("firebase-emulator-warning"),document.body.appendChild(e)}typeof console<"u"&&typeof console.info=="function"&&console.info("WARNING: You are using the Auth Emulator, which is intended for local testing only.  Do not use with production credentials."),typeof window<"u"&&typeof document<"u"&&(document.readyState==="loading"?window.addEventListener("DOMContentLoaded",t):t())}var j=class{constructor(e,n){this.providerId=e,this.signInMethod=n}toJSON(){return b("not implemented")}_getIdTokenResponse(e){return b("not implemented")}_linkToIdToken(e,n){return b("not implemented")}_getReauthenticationResolver(e){return b("not implemented")}};async function Ys(t,e){return g(t,"POST","/v1/accounts:signUp",e)}async function Xs(t,e){return $(t,"POST","/v1/accounts:signInWithPassword",p(t,e))}async function Qs(t,e){return $(t,"POST","/v1/accounts:signInWithEmailLink",p(t,e))}async function Zs(t,e){return $(t,"POST","/v1/accounts:signInWithEmailLink",p(t,e))}var de=class t extends j{constructor(e,n,r,i=null){super("password",r),this._email=e,this._password=n,this._tenantId=i}static _fromEmailAndPassword(e,n){return new t(e,n,"password")}static _fromEmailAndCode(e,n,r=null){return new t(e,n,"emailLink",r)}toJSON(){return{email:this._email,password:this._password,signInMethod:this.signInMethod,tenantId:this._tenantId}}static fromJSON(e){let n=typeof e=="string"?JSON.parse(e):e;if(n?.email&&n?.password){if(n.signInMethod==="password")return this._fromEmailAndPassword(n.email,n.password);if(n.signInMethod==="emailLink")return this._fromEmailAndCode(n.email,n.password,n.tenantId)}return null}async _getIdTokenResponse(e){switch(this.signInMethod){case"password":let n={returnSecureToken:!0,email:this._email,password:this._password,clientType:"CLIENT_TYPE_WEB"};return er(e,n,"signInWithPassword",Xs);case"emailLink":return Qs(e,{email:this._email,oobCode:this._password});default:w(e,"internal-error")}}async _linkToIdToken(e,n){switch(this.signInMethod){case"password":let r={idToken:n,returnSecureToken:!0,email:this._email,password:this._password,clientType:"CLIENT_TYPE_WEB"};return er(e,r,"signUpPassword",Ys);case"emailLink":return Zs(e,{idToken:n,email:this._email,oobCode:this._password});default:w(e,"internal-error")}}_getReauthenticationResolver(e){return this._getIdTokenResponse(e)}};async function ne(t,e){return $(t,"POST","/v1/accounts:signInWithIdp",p(t,e))}var eo="http://localhost",H=class t extends j{constructor(){super(...arguments),this.pendingToken=null}static _fromParams(e){let n=new t(e.providerId,e.signInMethod);return e.idToken||e.accessToken?(e.idToken&&(n.idToken=e.idToken),e.accessToken&&(n.accessToken=e.accessToken),e.nonce&&!e.pendingToken&&(n.nonce=e.nonce),e.pendingToken&&(n.pendingToken=e.pendingToken)):e.oauthToken&&e.oauthTokenSecret?(n.accessToken=e.oauthToken,n.secret=e.oauthTokenSecret):w("argument-error"),n}toJSON(){return{idToken:this.idToken,accessToken:this.accessToken,secret:this.secret,nonce:this.nonce,pendingToken:this.pendingToken,providerId:this.providerId,signInMethod:this.signInMethod}}static fromJSON(e){let n=typeof e=="string"?JSON.parse(e):e,{providerId:r,signInMethod:i}=n,s=Re(n,["providerId","signInMethod"]);if(!r||!i)return null;let o=new t(r,i);return o.idToken=s.idToken||void 0,o.accessToken=s.accessToken||void 0,o.secret=s.secret,o.nonce=s.nonce,o.pendingToken=s.pendingToken||null,o}_getIdTokenResponse(e){let n=this.buildRequest();return ne(e,n)}_linkToIdToken(e,n){let r=this.buildRequest();return r.idToken=n,ne(e,r)}_getReauthenticationResolver(e){let n=this.buildRequest();return n.autoCreate=!1,ne(e,n)}buildRequest(){let e={requestUri:eo,returnSecureToken:!0};if(this.pendingToken)e.pendingToken=this.pendingToken;else{let n={};this.idToken&&(n.id_token=this.idToken),this.accessToken&&(n.access_token=this.accessToken),this.secret&&(n.oauth_token_secret=this.secret),n.providerId=this.providerId,this.nonce&&!this.pendingToken&&(n.nonce=this.nonce),e.postBody=X(n)}return e}};async function to(t,e){return g(t,"POST","/v1/accounts:sendVerificationCode",p(t,e))}async function no(t,e){return $(t,"POST","/v1/accounts:signInWithPhoneNumber",p(t,e))}async function ro(t,e){let n=await $(t,"POST","/v1/accounts:signInWithPhoneNumber",p(t,e));if(n.temporaryProof)throw oe(t,"account-exists-with-different-credential",n);return n}var io={USER_NOT_FOUND:"user-not-found"};async function so(t,e){let n=Object.assign(Object.assign({},e),{operation:"REAUTH"});return $(t,"POST","/v1/accounts:signInWithPhoneNumber",p(t,n),io)}var he=class t extends j{constructor(e){super("phone","phone"),this.params=e}static _fromVerification(e,n){return new t({verificationId:e,verificationCode:n})}static _fromTokenResponse(e,n){return new t({phoneNumber:e,temporaryProof:n})}_getIdTokenResponse(e){return no(e,this._makeVerificationRequest())}_linkToIdToken(e,n){return ro(e,Object.assign({idToken:n},this._makeVerificationRequest()))}_getReauthenticationResolver(e){return so(e,this._makeVerificationRequest())}_makeVerificationRequest(){let{temporaryProof:e,phoneNumber:n,verificationId:r,verificationCode:i}=this.params;return e&&n?{temporaryProof:e,phoneNumber:n}:{sessionInfo:r,code:i}}toJSON(){let e={providerId:this.providerId};return this.params.phoneNumber&&(e.phoneNumber=this.params.phoneNumber),this.params.temporaryProof&&(e.temporaryProof=this.params.temporaryProof),this.params.verificationCode&&(e.verificationCode=this.params.verificationCode),this.params.verificationId&&(e.verificationId=this.params.verificationId),e}static fromJSON(e){typeof e=="string"&&(e=JSON.parse(e));let{verificationId:n,verificationCode:r,phoneNumber:i,temporaryProof:s}=e;return!r&&!n&&!i&&!s?null:new t({verificationId:n,verificationCode:r,phoneNumber:i,temporaryProof:s})}};function oo(t){switch(t){case"recoverEmail":return"RECOVER_EMAIL";case"resetPassword":return"PASSWORD_RESET";case"signIn":return"EMAIL_SIGNIN";case"verifyEmail":return"VERIFY_EMAIL";case"verifyAndChangeEmail":return"VERIFY_AND_CHANGE_EMAIL";case"revertSecondFactorAddition":return"REVERT_SECOND_FACTOR_ADDITION";default:return null}}function ao(t){let e=Q(Z(t)).link,n=e?Q(Z(e)).deep_link_id:null,r=Q(Z(t)).deep_link_id;return(r?Q(Z(r)).link:null)||r||n||e||t}var Ve=class t{constructor(e){var n,r,i,s,o,a;let c=Q(Z(e)),u=(n=c.apiKey)!==null&&n!==void 0?n:null,d=(r=c.oobCode)!==null&&r!==void 0?r:null,f=oo((i=c.mode)!==null&&i!==void 0?i:null);l(u&&d&&f,"argument-error"),this.apiKey=u,this.operation=f,this.code=d,this.continueUrl=(s=c.continueUrl)!==null&&s!==void 0?s:null,this.languageCode=(o=c.languageCode)!==null&&o!==void 0?o:null,this.tenantId=(a=c.tenantId)!==null&&a!==void 0?a:null}static parseLink(e){let n=ao(e);try{return new t(n)}catch{return null}}};var ie=class t{constructor(){this.providerId=t.PROVIDER_ID}static credential(e,n){return de._fromEmailAndPassword(e,n)}static credentialWithLink(e,n){let r=Ve.parseLink(n);return l(r,"argument-error"),de._fromEmailAndCode(e,r.code,r.tenantId)}};ie.PROVIDER_ID="password";ie.EMAIL_PASSWORD_SIGN_IN_METHOD="password";ie.EMAIL_LINK_SIGN_IN_METHOD="emailLink";var je=class{constructor(e){this.providerId=e,this.defaultLanguageCode=null,this.customParameters={}}setDefaultLanguage(e){this.defaultLanguageCode=e}setCustomParameters(e){return this.customParameters=e,this}getCustomParameters(){return this.customParameters}};var W=class extends je{constructor(){super(...arguments),this.scopes=[]}addScope(e){return this.scopes.includes(e)||this.scopes.push(e),this}getScopes(){return[...this.scopes]}};var fe=class t extends W{constructor(){super("facebook.com")}static credential(e){return H._fromParams({providerId:t.PROVIDER_ID,signInMethod:t.FACEBOOK_SIGN_IN_METHOD,accessToken:e})}static credentialFromResult(e){return t.credentialFromTaggedObject(e)}static credentialFromError(e){return t.credentialFromTaggedObject(e.customData||{})}static credentialFromTaggedObject({_tokenResponse:e}){if(!e||!("oauthAccessToken"in e)||!e.oauthAccessToken)return null;try{return t.credential(e.oauthAccessToken)}catch{return null}}};fe.FACEBOOK_SIGN_IN_METHOD="facebook.com";fe.PROVIDER_ID="facebook.com";var pe=class t extends W{constructor(){super("google.com"),this.addScope("profile")}static credential(e,n){return H._fromParams({providerId:t.PROVIDER_ID,signInMethod:t.GOOGLE_SIGN_IN_METHOD,idToken:e,accessToken:n})}static credentialFromResult(e){return t.credentialFromTaggedObject(e)}static credentialFromError(e){return t.credentialFromTaggedObject(e.customData||{})}static credentialFromTaggedObject({_tokenResponse:e}){if(!e)return null;let{oauthIdToken:n,oauthAccessToken:r}=e;if(!n&&!r)return null;try{return t.credential(n,r)}catch{return null}}};pe.GOOGLE_SIGN_IN_METHOD="google.com";pe.PROVIDER_ID="google.com";var me=class t extends W{constructor(){super("github.com")}static credential(e){return H._fromParams({providerId:t.PROVIDER_ID,signInMethod:t.GITHUB_SIGN_IN_METHOD,accessToken:e})}static credentialFromResult(e){return t.credentialFromTaggedObject(e)}static credentialFromError(e){return t.credentialFromTaggedObject(e.customData||{})}static credentialFromTaggedObject({_tokenResponse:e}){if(!e||!("oauthAccessToken"in e)||!e.oauthAccessToken)return null;try{return t.credential(e.oauthAccessToken)}catch{return null}}};me.GITHUB_SIGN_IN_METHOD="github.com";me.PROVIDER_ID="github.com";var ge=class t extends W{constructor(){super("twitter.com")}static credential(e,n){return H._fromParams({providerId:t.PROVIDER_ID,signInMethod:t.TWITTER_SIGN_IN_METHOD,oauthToken:e,oauthTokenSecret:n})}static credentialFromResult(e){return t.credentialFromTaggedObject(e)}static credentialFromError(e){return t.credentialFromTaggedObject(e.customData||{})}static credentialFromTaggedObject({_tokenResponse:e}){if(!e)return null;let{oauthAccessToken:n,oauthTokenSecret:r}=e;if(!n||!r)return null;try{return t.credential(n,r)}catch{return null}}};ge.TWITTER_SIGN_IN_METHOD="twitter.com";ge.PROVIDER_ID="twitter.com";var _e=class t{constructor(e){this.user=e.user,this.providerId=e.providerId,this._tokenResponse=e._tokenResponse,this.operationType=e.operationType}static async _fromIdTokenResponse(e,n,r,i=!1){let s=await re._fromIdTokenResponse(e,r,i),o=nr(r);return new t({user:s,providerId:o,_tokenResponse:r,operationType:n})}static async _forOperation(e,n,r){await e._updateTokensIfNecessary(r,!0);let i=nr(r);return new t({user:e,providerId:i,_tokenResponse:r,operationType:n})}};function nr(t){return t.providerId?t.providerId:"phoneNumber"in t?"phone":null}var $t=class t extends I{constructor(e,n,r,i){var s;super(n.code,n.message),this.operationType=r,this.user=i,Object.setPrototypeOf(this,t.prototype),this.customData={appName:e.name,tenantId:(s=e.tenantId)!==null&&s!==void 0?s:void 0,_serverResponse:n.customData._serverResponse,operationType:r}}static _fromErrorAndOperation(e,n,r,i){return new t(e,n,r,i)}};function Mr(t,e,n,r){return(e==="reauthenticate"?n._getReauthenticationResolver(t):n._getIdTokenResponse(t)).catch(s=>{throw s.code==="auth/multi-factor-auth-required"?$t._fromErrorAndOperation(t,s,e,r):s})}async function co(t,e,n=!1){let r=await ue(t,e._linkToIdToken(t.auth,await t.getIdToken()),n);return _e._forOperation(t,"link",r)}async function uo(t,e,n=!1){let{auth:r}=t;if(C(r.app))return Promise.reject(F(r));let i="reauthenticate";try{let s=await ue(t,Mr(r,i,e,t),n);l(s.idToken,r,"internal-error");let o=nn(s.idToken);l(o,r,"internal-error");let{sub:a}=o;return l(t.uid===a,r,"user-mismatch"),_e._forOperation(t,i,s)}catch(s){throw s?.code==="auth/user-not-found"&&w(r,"user-mismatch"),s}}async function lo(t,e,n=!1){if(C(t.app))return Promise.reject(F(t));let r="signIn",i=await Mr(t,r,e),s=await _e._fromIdTokenResponse(t,r,i);return n||await t._updateCurrentUser(s.user),s}function Ur(t,e,n,r){return O(t).onIdTokenChanged(e,n,r)}function xr(t,e,n){return O(t).beforeAuthStateChanged(e,n)}function ho(t,e){return g(t,"POST","/v2/accounts/mfaEnrollment:start",p(t,e))}function fo(t,e){return g(t,"POST","/v2/accounts/mfaEnrollment:finalize",p(t,e))}function po(t,e){return g(t,"POST","/v2/accounts/mfaEnrollment:start",p(t,e))}function mo(t,e){return g(t,"POST","/v2/accounts/mfaEnrollment:finalize",p(t,e))}var He="__sak";var We=class{constructor(e,n){this.storageRetriever=e,this.type=n}_isAvailable(){try{return this.storage?(this.storage.setItem(He,"1"),this.storage.removeItem(He),Promise.resolve(!0)):Promise.resolve(!1)}catch{return Promise.resolve(!1)}}_set(e,n){return this.storage.setItem(e,JSON.stringify(n)),Promise.resolve()}_get(e){let n=this.storage.getItem(e);return Promise.resolve(n?JSON.parse(n):null)}_remove(e){return this.storage.removeItem(e),Promise.resolve()}get storage(){return this.storageRetriever()}};var go=1e3,_o=10,Be=class extends We{constructor(){super(()=>window.localStorage,"LOCAL"),this.boundEventHandler=(e,n)=>this.onStorageEvent(e,n),this.listeners={},this.localCache={},this.pollTimer=null,this.fallbackToPolling=Or(),this._shouldAllowMigration=!0}forAllChangedKeys(e){for(let n of Object.keys(this.listeners)){let r=this.storage.getItem(n),i=this.localCache[n];r!==i&&e(n,i,r)}}onStorageEvent(e,n=!1){if(!e.key){this.forAllChangedKeys((o,a,c)=>{this.notifyListeners(o,c)});return}let r=e.key;n?this.detachListener():this.stopPolling();let i=()=>{let o=this.storage.getItem(r);!n&&this.localCache[r]===o||this.notifyListeners(r,o)},s=this.storage.getItem(r);Vs()&&s!==e.newValue&&e.newValue!==e.oldValue?setTimeout(i,_o):i()}notifyListeners(e,n){this.localCache[e]=n;let r=this.listeners[e];if(r)for(let i of Array.from(r))i(n&&JSON.parse(n))}startPolling(){this.stopPolling(),this.pollTimer=setInterval(()=>{this.forAllChangedKeys((e,n,r)=>{this.onStorageEvent(new StorageEvent("storage",{key:e,oldValue:n,newValue:r}),!0)})},go)}stopPolling(){this.pollTimer&&(clearInterval(this.pollTimer),this.pollTimer=null)}attachListener(){window.addEventListener("storage",this.boundEventHandler)}detachListener(){window.removeEventListener("storage",this.boundEventHandler)}_addListener(e,n){Object.keys(this.listeners).length===0&&(this.fallbackToPolling?this.startPolling():this.attachListener()),this.listeners[e]||(this.listeners[e]=new Set,this.localCache[e]=this.storage.getItem(e)),this.listeners[e].add(n)}_removeListener(e,n){this.listeners[e]&&(this.listeners[e].delete(n),this.listeners[e].size===0&&delete this.listeners[e]),Object.keys(this.listeners).length===0&&(this.detachListener(),this.stopPolling())}async _set(e,n){await super._set(e,n),this.localCache[e]=JSON.stringify(n)}async _get(e){let n=await super._get(e);return this.localCache[e]=JSON.stringify(n),n}async _remove(e){await super._remove(e),delete this.localCache[e]}};Be.type="LOCAL";var Fr=Be;var $e=class extends We{constructor(){super(()=>window.sessionStorage,"SESSION")}_addListener(e,n){}_removeListener(e,n){}};$e.type="SESSION";var sn=$e;function Io(t){return Promise.all(t.map(async e=>{try{return{fulfilled:!0,value:await e}}catch(n){return{fulfilled:!1,reason:n}}}))}var qe=class t{constructor(e){this.eventTarget=e,this.handlersMap={},this.boundEventHandler=this.handleEvent.bind(this)}static _getInstance(e){let n=this.receivers.find(i=>i.isListeningto(e));if(n)return n;let r=new t(e);return this.receivers.push(r),r}isListeningto(e){return this.eventTarget===e}async handleEvent(e){let n=e,{eventId:r,eventType:i,data:s}=n.data,o=this.handlersMap[i];if(!o?.size)return;n.ports[0].postMessage({status:"ack",eventId:r,eventType:i});let a=Array.from(o).map(async u=>u(n.origin,s)),c=await Io(a);n.ports[0].postMessage({status:"done",eventId:r,eventType:i,response:c})}_subscribe(e,n){Object.keys(this.handlersMap).length===0&&this.eventTarget.addEventListener("message",this.boundEventHandler),this.handlersMap[e]||(this.handlersMap[e]=new Set),this.handlersMap[e].add(n)}_unsubscribe(e,n){this.handlersMap[e]&&n&&this.handlersMap[e].delete(n),(!n||this.handlersMap[e].size===0)&&delete this.handlersMap[e],Object.keys(this.handlersMap).length===0&&this.eventTarget.removeEventListener("message",this.boundEventHandler)}};qe.receivers=[];function on(t="",e=10){let n="";for(let r=0;r<e;r++)n+=Math.floor(Math.random()*10);return t+n}var qt=class{constructor(e){this.target=e,this.handlers=new Set}removeMessageHandler(e){e.messageChannel&&(e.messageChannel.port1.removeEventListener("message",e.onMessage),e.messageChannel.port1.close()),this.handlers.delete(e)}async _send(e,n,r=50){let i=typeof MessageChannel<"u"?new MessageChannel:null;if(!i)throw new Error("connection_unavailable");let s,o;return new Promise((a,c)=>{let u=on("",20);i.port1.start();let d=setTimeout(()=>{c(new Error("unsupported_event"))},r);o={messageChannel:i,onMessage(f){let _=f;if(_.data.eventId===u)switch(_.data.status){case"ack":clearTimeout(d),s=setTimeout(()=>{c(new Error("timeout"))},3e3);break;case"done":clearTimeout(s),a(_.data.response);break;default:clearTimeout(d),clearTimeout(s),c(new Error("invalid_response"));break}}},this.handlers.add(o),i.port1.addEventListener("message",o.onMessage),this.target.postMessage({eventType:e,eventId:u,data:n},[i.port2])}).finally(()=>{o&&this.removeMessageHandler(o)})}};function S(){return window}function vo(t){S().location.href=t}function Vr(){return typeof S().WorkerGlobalScope<"u"&&typeof S().importScripts=="function"}async function yo(){if(!navigator?.serviceWorker)return null;try{return(await navigator.serviceWorker.ready).active}catch{return null}}function Eo(){var t;return((t=navigator?.serviceWorker)===null||t===void 0?void 0:t.controller)||null}function wo(){return Vr()?self:null}var jr="firebaseLocalStorageDb",To=1,ze="firebaseLocalStorage",Hr="fbase_key",B=class{constructor(e){this.request=e}toPromise(){return new Promise((e,n)=>{this.request.addEventListener("success",()=>{e(this.request.result)}),this.request.addEventListener("error",()=>{n(this.request.error)})})}};function nt(t,e){return t.transaction([ze],e?"readwrite":"readonly").objectStore(ze)}function bo(){let t=indexedDB.deleteDatabase(jr);return new B(t).toPromise()}function zt(){let t=indexedDB.open(jr,To);return new Promise((e,n)=>{t.addEventListener("error",()=>{n(t.error)}),t.addEventListener("upgradeneeded",()=>{let r=t.result;try{r.createObjectStore(ze,{keyPath:Hr})}catch(i){n(i)}}),t.addEventListener("success",async()=>{let r=t.result;r.objectStoreNames.contains(ze)?e(r):(r.close(),await bo(),e(await zt()))})})}async function rr(t,e,n){let r=nt(t,!0).put({[Hr]:e,value:n});return new B(r).toPromise()}async function Ao(t,e){let n=nt(t,!1).get(e),r=await new B(n).toPromise();return r===void 0?null:r.value}function ir(t,e){let n=nt(t,!0).delete(e);return new B(n).toPromise()}var So=800,Ro=3,Ge=class{constructor(){this.type="LOCAL",this._shouldAllowMigration=!0,this.listeners={},this.localCache={},this.pollTimer=null,this.pendingWrites=0,this.receiver=null,this.sender=null,this.serviceWorkerReceiverAvailable=!1,this.activeServiceWorker=null,this._workerInitializationPromise=this.initializeServiceWorkerMessaging().then(()=>{},()=>{})}async _openDb(){return this.db?this.db:(this.db=await zt(),this.db)}async _withRetries(e){let n=0;for(;;)try{let r=await this._openDb();return await e(r)}catch(r){if(n++>Ro)throw r;this.db&&(this.db.close(),this.db=void 0)}}async initializeServiceWorkerMessaging(){return Vr()?this.initializeReceiver():this.initializeSender()}async initializeReceiver(){this.receiver=qe._getInstance(wo()),this.receiver._subscribe("keyChanged",async(e,n)=>({keyProcessed:(await this._poll()).includes(n.key)})),this.receiver._subscribe("ping",async(e,n)=>["keyChanged"])}async initializeSender(){var e,n;if(this.activeServiceWorker=await yo(),!this.activeServiceWorker)return;this.sender=new qt(this.activeServiceWorker);let r=await this.sender._send("ping",{},800);r&&!((e=r[0])===null||e===void 0)&&e.fulfilled&&!((n=r[0])===null||n===void 0)&&n.value.includes("keyChanged")&&(this.serviceWorkerReceiverAvailable=!0)}async notifyServiceWorker(e){if(!(!this.sender||!this.activeServiceWorker||Eo()!==this.activeServiceWorker))try{await this.sender._send("keyChanged",{key:e},this.serviceWorkerReceiverAvailable?800:50)}catch{}}async _isAvailable(){try{if(!indexedDB)return!1;let e=await zt();return await rr(e,He,"1"),await ir(e,He),!0}catch{}return!1}async _withPendingWrite(e){this.pendingWrites++;try{await e()}finally{this.pendingWrites--}}async _set(e,n){return this._withPendingWrite(async()=>(await this._withRetries(r=>rr(r,e,n)),this.localCache[e]=n,this.notifyServiceWorker(e)))}async _get(e){let n=await this._withRetries(r=>Ao(r,e));return this.localCache[e]=n,n}async _remove(e){return this._withPendingWrite(async()=>(await this._withRetries(n=>ir(n,e)),delete this.localCache[e],this.notifyServiceWorker(e)))}async _poll(){let e=await this._withRetries(i=>{let s=nt(i,!1).getAll();return new B(s).toPromise()});if(!e)return[];if(this.pendingWrites!==0)return[];let n=[],r=new Set;if(e.length!==0)for(let{fbase_key:i,value:s}of e)r.add(i),JSON.stringify(this.localCache[i])!==JSON.stringify(s)&&(this.notifyListeners(i,s),n.push(i));for(let i of Object.keys(this.localCache))this.localCache[i]&&!r.has(i)&&(this.notifyListeners(i,null),n.push(i));return n}notifyListeners(e,n){this.localCache[e]=n;let r=this.listeners[e];if(r)for(let i of Array.from(r))i(n)}startPolling(){this.stopPolling(),this.pollTimer=setInterval(async()=>this._poll(),So)}stopPolling(){this.pollTimer&&(clearInterval(this.pollTimer),this.pollTimer=null)}_addListener(e,n){Object.keys(this.listeners).length===0&&this.startPolling(),this.listeners[e]||(this.listeners[e]=new Set,this._get(e)),this.listeners[e].add(n)}_removeListener(e,n){this.listeners[e]&&(this.listeners[e].delete(n),this.listeners[e].size===0&&delete this.listeners[e]),Object.keys(this.listeners).length===0&&this.stopPolling()}};Ge.type="LOCAL";var Wr=Ge;function Oo(t,e){return g(t,"POST","/v2/accounts/mfaSignIn:start",p(t,e))}function ko(t,e){return g(t,"POST","/v2/accounts/mfaSignIn:finalize",p(t,e))}function Po(t,e){return g(t,"POST","/v2/accounts/mfaSignIn:finalize",p(t,e))}var Vc=Cr("rcb"),jc=new V(3e4,6e4);var Co="recaptcha";async function No(t,e,n){var r;let i=await n.verify();try{l(typeof i=="string",t,"argument-error"),l(n.type===Co,t,"argument-error");let s;if(typeof e=="string"?s={phoneNumber:e}:s=e,"session"in s){let o=s.session;if("phoneNumber"in s)return l(o.type==="enroll",t,"internal-error"),(await ho(t,{idToken:o.credential,phoneEnrollmentInfo:{phoneNumber:s.phoneNumber,recaptchaToken:i}})).phoneSessionInfo.sessionInfo;{l(o.type==="signin",t,"internal-error");let a=((r=s.multiFactorHint)===null||r===void 0?void 0:r.uid)||s.multiFactorUid;return l(a,t,"missing-multi-factor-info"),(await Oo(t,{mfaPendingCredential:o.credential,mfaEnrollmentId:a,phoneSignInInfo:{recaptchaToken:i}})).phoneResponseInfo.sessionInfo}}else{let{sessionInfo:o}=await to(t,{phoneNumber:s.phoneNumber,recaptchaToken:i});return o}}finally{n._reset()}}var Ie=class t{constructor(e){this.providerId=t.PROVIDER_ID,this.auth=ye(e)}verifyPhoneNumber(e,n){return No(this.auth,e,O(n))}static credential(e,n){return he._fromVerification(e,n)}static credentialFromResult(e){let n=e;return t.credentialFromTaggedObject(n)}static credentialFromError(e){return t.credentialFromTaggedObject(e.customData||{})}static credentialFromTaggedObject({_tokenResponse:e}){if(!e)return null;let{phoneNumber:n,temporaryProof:r}=e;return n&&r?he._fromTokenResponse(n,r):null}};Ie.PROVIDER_ID="phone";Ie.PHONE_SIGN_IN_METHOD="phone";function Do(t,e){return e?N(e):(l(t._popupRedirectResolver,t,"argument-error"),t._popupRedirectResolver)}var ve=class extends j{constructor(e){super("custom","custom"),this.params=e}_getIdTokenResponse(e){return ne(e,this._buildIdpRequest())}_linkToIdToken(e,n){return ne(e,this._buildIdpRequest(n))}_getReauthenticationResolver(e){return ne(e,this._buildIdpRequest())}_buildIdpRequest(e){let n={requestUri:this.params.requestUri,sessionId:this.params.sessionId,postBody:this.params.postBody,tenantId:this.params.tenantId,pendingToken:this.params.pendingToken,returnSecureToken:!0,returnIdpCredential:!0};return e&&(n.idToken=e),n}};function Lo(t){return lo(t.auth,new ve(t),t.bypassAuthState)}function Mo(t){let{auth:e,user:n}=t;return l(n,e,"internal-error"),uo(n,new ve(t),t.bypassAuthState)}async function Uo(t){let{auth:e,user:n}=t;return l(n,e,"internal-error"),co(n,new ve(t),t.bypassAuthState)}var Ke=class{constructor(e,n,r,i,s=!1){this.auth=e,this.resolver=r,this.user=i,this.bypassAuthState=s,this.pendingPromise=null,this.eventManager=null,this.filter=Array.isArray(n)?n:[n]}execute(){return new Promise(async(e,n)=>{this.pendingPromise={resolve:e,reject:n};try{this.eventManager=await this.resolver._initialize(this.auth),await this.onExecution(),this.eventManager.registerConsumer(this)}catch(r){this.reject(r)}})}async onAuthEvent(e){let{urlResponse:n,sessionId:r,postBody:i,tenantId:s,error:o,type:a}=e;if(o){this.reject(o);return}let c={auth:this.auth,requestUri:n,sessionId:r,tenantId:s||void 0,postBody:i||void 0,user:this.user,bypassAuthState:this.bypassAuthState};try{this.resolve(await this.getIdpTask(a)(c))}catch(u){this.reject(u)}}onError(e){this.reject(e)}getIdpTask(e){switch(e){case"signInViaPopup":case"signInViaRedirect":return Lo;case"linkViaPopup":case"linkViaRedirect":return Uo;case"reauthViaPopup":case"reauthViaRedirect":return Mo;default:w(this.auth,"internal-error")}}resolve(e){D(this.pendingPromise,"Pending promise was never set"),this.pendingPromise.resolve(e),this.unregisterAndCleanUp()}reject(e){D(this.pendingPromise,"Pending promise was never set"),this.pendingPromise.reject(e),this.unregisterAndCleanUp()}unregisterAndCleanUp(){this.eventManager&&this.eventManager.unregisterConsumer(this),this.pendingPromise=null,this.cleanUp()}};var xo=new V(2e3,1e4);var Gt=class t extends Ke{constructor(e,n,r,i,s){super(e,n,i,s),this.provider=r,this.authWindow=null,this.pollId=null,t.currentPopupAction&&t.currentPopupAction.cancel(),t.currentPopupAction=this}async executeNotNull(){let e=await this.execute();return l(e,this.auth,"internal-error"),e}async onExecution(){D(this.filter.length===1,"Popup operations only handle one event");let e=on();this.authWindow=await this.resolver._openPopup(this.auth,this.provider,this.filter[0],e),this.authWindow.associatedEvent=e,this.resolver._originValidation(this.auth).catch(n=>{this.reject(n)}),this.resolver._isIframeWebStorageSupported(this.auth,n=>{n||this.reject(A(this.auth,"web-storage-unsupported"))}),this.pollUserCancellation()}get eventId(){var e;return((e=this.authWindow)===null||e===void 0?void 0:e.associatedEvent)||null}cancel(){this.reject(A(this.auth,"cancelled-popup-request"))}cleanUp(){this.authWindow&&this.authWindow.close(),this.pollId&&window.clearTimeout(this.pollId),this.authWindow=null,this.pollId=null,t.currentPopupAction=null}pollUserCancellation(){let e=()=>{var n,r;if(!((r=(n=this.authWindow)===null||n===void 0?void 0:n.window)===null||r===void 0)&&r.closed){this.pollId=window.setTimeout(()=>{this.pollId=null,this.reject(A(this.auth,"popup-closed-by-user"))},8e3);return}this.pollId=window.setTimeout(e,xo.get())};e()}};Gt.currentPopupAction=null;var Fo="pendingRedirect",Ce=new Map,Kt=class extends Ke{constructor(e,n,r=!1){super(e,["signInViaRedirect","linkViaRedirect","reauthViaRedirect","unknown"],n,void 0,r),this.eventId=null}async execute(){let e=Ce.get(this.auth._key());if(!e){try{let r=await Vo(this.resolver,this.auth)?await super.execute():null;e=()=>Promise.resolve(r)}catch(n){e=()=>Promise.reject(n)}Ce.set(this.auth._key(),e)}return this.bypassAuthState||Ce.set(this.auth._key(),()=>Promise.resolve(null)),e()}async onAuthEvent(e){if(e.type==="signInViaRedirect")return super.onAuthEvent(e);if(e.type==="unknown"){this.resolve(null);return}if(e.eventId){let n=await this.auth._redirectUserForId(e.eventId);if(n)return this.user=n,super.onAuthEvent(e);this.resolve(null)}}async onExecution(){}cleanUp(){}};async function Vo(t,e){let n=Wo(e),r=Ho(t);if(!await r._isAvailable())return!1;let i=await r._get(n)==="true";return await r._remove(n),i}function jo(t,e){Ce.set(t._key(),e)}function Ho(t){return N(t._redirectPersistence)}function Wo(t){return Pe(Fo,t.config.apiKey,t.name)}async function Bo(t,e,n=!1){if(C(t.app))return Promise.reject(F(t));let r=ye(t),i=Do(r,e),o=await new Kt(r,i,n).execute();return o&&!n&&(delete o.user._redirectEventId,await r._persistUserIfCurrent(o.user),await r._setRedirectUser(null,e)),o}var $o=10*60*1e3,Jt=class{constructor(e){this.auth=e,this.cachedEventUids=new Set,this.consumers=new Set,this.queuedRedirectEvent=null,this.hasHandledPotentialRedirect=!1,this.lastProcessedEventTime=Date.now()}registerConsumer(e){this.consumers.add(e),this.queuedRedirectEvent&&this.isEventForConsumer(this.queuedRedirectEvent,e)&&(this.sendToConsumer(this.queuedRedirectEvent,e),this.saveEventToCache(this.queuedRedirectEvent),this.queuedRedirectEvent=null)}unregisterConsumer(e){this.consumers.delete(e)}onEvent(e){if(this.hasEventBeenHandled(e))return!1;let n=!1;return this.consumers.forEach(r=>{this.isEventForConsumer(e,r)&&(n=!0,this.sendToConsumer(e,r),this.saveEventToCache(e))}),this.hasHandledPotentialRedirect||!qo(e)||(this.hasHandledPotentialRedirect=!0,n||(this.queuedRedirectEvent=e,n=!0)),n}sendToConsumer(e,n){var r;if(e.error&&!Br(e)){let i=((r=e.error.code)===null||r===void 0?void 0:r.split("auth/")[1])||"internal-error";n.onError(A(this.auth,i))}else n.onAuthEvent(e)}isEventForConsumer(e,n){let r=n.eventId===null||!!e.eventId&&e.eventId===n.eventId;return n.filter.includes(e.type)&&r}hasEventBeenHandled(e){return Date.now()-this.lastProcessedEventTime>=$o&&this.cachedEventUids.clear(),this.cachedEventUids.has(sr(e))}saveEventToCache(e){this.cachedEventUids.add(sr(e)),this.lastProcessedEventTime=Date.now()}};function sr(t){return[t.type,t.eventId,t.sessionId,t.tenantId].filter(e=>e).join("-")}function Br({type:t,error:e}){return t==="unknown"&&e?.code==="auth/no-auth-event"}function qo(t){switch(t.type){case"signInViaRedirect":case"linkViaRedirect":case"reauthViaRedirect":return!0;case"unknown":return Br(t);default:return!1}}async function zo(t,e={}){return g(t,"GET","/v1/projects",e)}var Go=/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/,Ko=/^https?/;async function Jo(t){if(t.config.emulator)return;let{authorizedDomains:e}=await zo(t);for(let n of e)try{if(Yo(n))return}catch{}w(t,"unauthorized-domain")}function Yo(t){let e=Mt(),{protocol:n,hostname:r}=new URL(e);if(t.startsWith("chrome-extension://")){let o=new URL(t);return o.hostname===""&&r===""?n==="chrome-extension:"&&t.replace("chrome-extension://","")===e.replace("chrome-extension://",""):n==="chrome-extension:"&&o.hostname===r}if(!Ko.test(n))return!1;if(Go.test(t))return r===t;let i=t.replace(/\./g,"\\.");return new RegExp("^(.+\\."+i+"|"+i+")$","i").test(r)}var Xo=new V(3e4,6e4);function or(){let t=S().___jsl;if(t?.H){for(let e of Object.keys(t.H))if(t.H[e].r=t.H[e].r||[],t.H[e].L=t.H[e].L||[],t.H[e].r=[...t.H[e].L],t.CP)for(let n=0;n<t.CP.length;n++)t.CP[n]=null}}function Qo(t){return new Promise((e,n)=>{var r,i,s;function o(){or(),gapi.load("gapi.iframes",{callback:()=>{e(gapi.iframes.getContext())},ontimeout:()=>{or(),n(A(t,"network-request-failed"))},timeout:Xo.get()})}if(!((i=(r=S().gapi)===null||r===void 0?void 0:r.iframes)===null||i===void 0)&&i.Iframe)e(gapi.iframes.getContext());else if(!((s=S().gapi)===null||s===void 0)&&s.load)o();else{let a=Cr("iframefcb");return S()[a]=()=>{gapi.load?o():n(A(t,"network-request-failed"))},Pr(`${$s()}?onload=${a}`).catch(c=>n(c))}}).catch(e=>{throw Ne=null,e})}var Ne=null;function Zo(t){return Ne=Ne||Qo(t),Ne}var ea=new V(5e3,15e3),ta="__/auth/iframe",na="emulator/auth/iframe",ra={style:{position:"absolute",top:"-100px",width:"1px",height:"1px"},"aria-hidden":"true",tabindex:"-1"},ia=new Map([["identitytoolkit.googleapis.com","p"],["staging-identitytoolkit.sandbox.googleapis.com","s"],["test-identitytoolkit.sandbox.googleapis.com","t"]]);function sa(t){let e=t.config;l(e.authDomain,t,"auth-domain-config-required");let n=e.emulator?en(e,na):`https://${t.config.authDomain}/${ta}`,r={apiKey:e.apiKey,appName:t.name,v:te},i=ia.get(t.config.apiHost);i&&(r.eid=i);let s=t._getFrameworks();return s.length&&(r.fw=s.join(",")),`${n}?${X(r).slice(1)}`}async function oa(t){let e=await Zo(t),n=S().gapi;return l(n,t,"internal-error"),e.open({where:document.body,url:sa(t),messageHandlersFilter:n.iframes.CROSS_ORIGIN_IFRAMES_FILTER,attributes:ra,dontclear:!0},r=>new Promise(async(i,s)=>{await r.restyle({setHideOnLeave:!1});let o=A(t,"network-request-failed"),a=S().setTimeout(()=>{s(o)},ea.get());function c(){S().clearTimeout(a),i(r)}r.ping(c).then(c,()=>{s(o)})}))}var aa={location:"yes",resizable:"yes",statusbar:"yes",toolbar:"no"},ca=500,ua=600,la="_blank",da="http://localhost",Je=class{constructor(e){this.window=e,this.associatedEvent=null}close(){if(this.window)try{this.window.close()}catch{}}};function ha(t,e,n,r=ca,i=ua){let s=Math.max((window.screen.availHeight-i)/2,0).toString(),o=Math.max((window.screen.availWidth-r)/2,0).toString(),a="",c=Object.assign(Object.assign({},aa),{width:r.toString(),height:i.toString(),top:s,left:o}),u=m().toLowerCase();n&&(a=Tr(u)?la:n),Er(u)&&(e=e||da,c.scrollbars="yes");let d=Object.entries(c).reduce((_,[R,J])=>`${_}${R}=${J},`,"");if(Fs(u)&&a!=="_self")return fa(e||"",a),new Je(null);let f=window.open(e||"",a,d);l(f,t,"popup-blocked");try{f.focus()}catch{}return new Je(f)}function fa(t,e){let n=document.createElement("a");n.href=t,n.target=e;let r=document.createEvent("MouseEvent");r.initMouseEvent("click",!0,!0,window,1,0,0,0,0,!1,!1,!1,!1,1,null),n.dispatchEvent(r)}var pa="__/auth/handler",ma="emulator/auth/handler",ga=encodeURIComponent("fac");async function ar(t,e,n,r,i,s){l(t.config.authDomain,t,"auth-domain-config-required"),l(t.config.apiKey,t,"invalid-api-key");let o={apiKey:t.config.apiKey,appName:t.name,authType:n,redirectUrl:r,v:te,eventId:i};if(e instanceof je){e.setDefaultLanguage(t.languageCode),o.providerId=e.providerId||"",Dn(e.getCustomParameters())||(o.customParameters=JSON.stringify(e.getCustomParameters()));for(let[d,f]of Object.entries(s||{}))o[d]=f}if(e instanceof W){let d=e.getScopes().filter(f=>f!=="");d.length>0&&(o.scopes=d.join(","))}t.tenantId&&(o.tid=t.tenantId);let a=o;for(let d of Object.keys(a))a[d]===void 0&&delete a[d];let c=await t._getAppCheckToken(),u=c?`#${ga}=${encodeURIComponent(c)}`:"";return`${_a(t)}?${X(a).slice(1)}${u}`}function _a({config:t}){return t.emulator?en(t,ma):`https://${t.authDomain}/${pa}`}var Lt="webStorageSupport",Yt=class{constructor(){this.eventManagers={},this.iframes={},this.originValidationPromises={},this._redirectPersistence=sn,this._completeRedirectFn=Bo,this._overrideRedirectResult=jo}async _openPopup(e,n,r,i){var s;D((s=this.eventManagers[e._key()])===null||s===void 0?void 0:s.manager,"_initialize() not called before _openPopup()");let o=await ar(e,n,r,Mt(),i);return ha(e,o,on())}async _openRedirect(e,n,r,i){await this._originValidation(e);let s=await ar(e,n,r,Mt(),i);return vo(s),new Promise(()=>{})}_initialize(e){let n=e._key();if(this.eventManagers[n]){let{manager:i,promise:s}=this.eventManagers[n];return i?Promise.resolve(i):(D(s,"If manager is not set, promise should be"),s)}let r=this.initAndGetManager(e);return this.eventManagers[n]={promise:r},r.catch(()=>{delete this.eventManagers[n]}),r}async initAndGetManager(e){let n=await oa(e),r=new Jt(e);return n.register("authEvent",i=>(l(i?.authEvent,e,"invalid-auth-event"),{status:r.onEvent(i.authEvent)?"ACK":"ERROR"}),gapi.iframes.CROSS_ORIGIN_IFRAMES_FILTER),this.eventManagers[e._key()]={manager:r},this.iframes[e._key()]=n,r}_isIframeWebStorageSupported(e,n){this.iframes[e._key()].send(Lt,{type:Lt},i=>{var s;let o=(s=i?.[0])===null||s===void 0?void 0:s[Lt];o!==void 0&&n(!!o),w(e,"internal-error")},gapi.iframes.CROSS_ORIGIN_IFRAMES_FILTER)}_originValidation(e){let n=e._key();return this.originValidationPromises[n]||(this.originValidationPromises[n]=Jo(e)),this.originValidationPromises[n]}get _shouldInitProactively(){return Or()||wr()||rn()}},$r=Yt,Ye=class{constructor(e){this.factorId=e}_process(e,n,r){switch(n.type){case"enroll":return this._finalizeEnroll(e,n.credential,r);case"signin":return this._finalizeSignIn(e,n.credential);default:return b("unexpected MultiFactorSessionType")}}},Xt=class t extends Ye{constructor(e){super("phone"),this.credential=e}static _fromCredential(e){return new t(e)}_finalizeEnroll(e,n,r){return fo(e,{idToken:n,displayName:r,phoneVerificationInfo:this.credential._makeVerificationRequest()})}_finalizeSignIn(e,n){return ko(e,{mfaPendingCredential:n,phoneVerificationInfo:this.credential._makeVerificationRequest()})}},Xe=class{constructor(){}static assertion(e){return Xt._fromCredential(e)}};Xe.FACTOR_ID="phone";var Qe=class{static assertionForEnrollment(e,n){return Ze._fromSecret(e,n)}static assertionForSignIn(e,n){return Ze._fromEnrollmentId(e,n)}static async generateSecret(e){var n;let r=e;l(typeof((n=r.user)===null||n===void 0?void 0:n.auth)<"u","internal-error");let i=await po(r.user.auth,{idToken:r.credential,totpEnrollmentInfo:{}});return et._fromStartTotpMfaEnrollmentResponse(i,r.user.auth)}};Qe.FACTOR_ID="totp";var Ze=class t extends Ye{constructor(e,n,r){super("totp"),this.otp=e,this.enrollmentId=n,this.secret=r}static _fromSecret(e,n){return new t(n,void 0,e)}static _fromEnrollmentId(e,n){return new t(n,e)}async _finalizeEnroll(e,n,r){return l(typeof this.secret<"u",e,"argument-error"),mo(e,{idToken:n,displayName:r,totpVerificationInfo:this.secret._makeTotpVerificationInfo(this.otp)})}async _finalizeSignIn(e,n){l(this.enrollmentId!==void 0&&this.otp!==void 0,e,"argument-error");let r={verificationCode:this.otp};return Po(e,{mfaPendingCredential:n,mfaEnrollmentId:this.enrollmentId,totpVerificationInfo:r})}},et=class t{constructor(e,n,r,i,s,o,a){this.sessionInfo=o,this.auth=a,this.secretKey=e,this.hashingAlgorithm=n,this.codeLength=r,this.codeIntervalSeconds=i,this.enrollmentCompletionDeadline=s}static _fromStartTotpMfaEnrollmentResponse(e,n){return new t(e.totpSessionInfo.sharedSecretKey,e.totpSessionInfo.hashingAlgorithm,e.totpSessionInfo.verificationCodeLength,e.totpSessionInfo.periodSec,new Date(e.totpSessionInfo.finalizeEnrollmentTime).toUTCString(),e.totpSessionInfo.sessionInfo,n)}_makeTotpVerificationInfo(e){return{sessionInfo:this.sessionInfo,verificationCode:e}}generateQrCodeUrl(e,n){var r;let i=!1;return(Oe(e)||Oe(n))&&(i=!0),i&&(Oe(e)&&(e=((r=this.auth.currentUser)===null||r===void 0?void 0:r.email)||"unknownuser"),Oe(n)&&(n=this.auth.name)),`otpauth://totp/${n}:${e}?secret=${this.secretKey}&issuer=${n}&algorithm=${this.hashingAlgorithm}&digits=${this.codeLength}`}};function Oe(t){return typeof t>"u"||t?.length===0}var cr="@firebase/auth",ur="1.7.9";var Qt=class{constructor(e){this.auth=e,this.internalListeners=new Map}getUid(){var e;return this.assertAuthConfigured(),((e=this.auth.currentUser)===null||e===void 0?void 0:e.uid)||null}async getToken(e){return this.assertAuthConfigured(),await this.auth._initializationPromise,this.auth.currentUser?{accessToken:await this.auth.currentUser.getIdToken(e)}:null}addAuthTokenListener(e){if(this.assertAuthConfigured(),this.internalListeners.has(e))return;let n=this.auth.onIdTokenChanged(r=>{e(r?.stsTokenManager.accessToken||null)});this.internalListeners.set(e,n),this.updateProactiveRefresh()}removeAuthTokenListener(e){this.assertAuthConfigured();let n=this.internalListeners.get(e);n&&(this.internalListeners.delete(e),n(),this.updateProactiveRefresh())}assertAuthConfigured(){l(this.auth._initializationPromise,"dependent-sdk-initialized-before-auth")}updateProactiveRefresh(){this.internalListeners.size>0?this.auth._startProactiveRefresh():this.auth._stopProactiveRefresh()}};function Ia(t){switch(t){case"Node":return"node";case"ReactNative":return"rn";case"Worker":return"webworker";case"Cordova":return"cordova";case"WebExtension":return"web-extension";default:return}}function va(t){P(new v("auth",(e,{options:n})=>{let r=e.getProvider("app").getImmediate(),i=e.getProvider("heartbeat"),s=e.getProvider("app-check-internal"),{apiKey:o,authDomain:a}=r.options;l(o&&!o.includes(":"),"invalid-api-key",{appName:r.name});let c={apiKey:o,authDomain:a,clientPlatform:t,apiHost:"identitytoolkit.googleapis.com",tokenApiHost:"securetoken.googleapis.com",apiScheme:"https",sdkClientVersion:kr(t)},u=new Wt(r,i,s,c);return Gs(u,n),u},"PUBLIC").setInstantiationMode("EXPLICIT").setInstanceCreatedCallback((e,n,r)=>{e.getProvider("auth-internal").initialize()})),P(new v("auth-internal",e=>{let n=ye(e.getProvider("auth").getImmediate());return(r=>new Qt(r))(n)},"PRIVATE").setInstantiationMode("EXPLICIT")),E(cr,ur,Ia(t)),E(cr,ur,"esm2017")}var ya=5*60,Ea=_t("authIdTokenMaxAge")||ya,lr=null,wa=t=>async e=>{let n=e&&await e.getIdTokenResult(),r=n&&(new Date().getTime()-Date.parse(n.issuedAtTime))/1e3;if(r&&r>Ea)return;let i=n?.token;lr!==i&&(lr=i,await fetch(t,{method:i?"POST":"DELETE",headers:i?{Authorization:`Bearer ${i}`}:{}}))};function an(t=Se()){let e=x(t,"auth");if(e.isInitialized())return e.getImmediate();let n=Nr(t,{popupRedirectResolver:$r,persistence:[Wr,Fr,sn]}),r=_t("authTokenSyncURL");if(r&&typeof isSecureContext=="boolean"&&isSecureContext){let s=new URL(r,location.origin);if(location.origin===s.origin){let o=wa(s.toString());xr(n,o,()=>o(n.currentUser)),Ur(n,a=>o(a))}}let i=An("auth");return i&&Dr(n,`http://${i}`),n}function Ta(){var t,e;return(e=(t=document.getElementsByTagName("head"))===null||t===void 0?void 0:t[0])!==null&&e!==void 0?e:document}Ws({loadJS(t){return new Promise((e,n)=>{let r=document.createElement("script");r.setAttribute("src",t),r.onload=e,r.onerror=i=>{let s=A("internal-error");s.customData=i,n(s)},r.type="text/javascript",r.charset="UTF-8",Ta().appendChild(r)})},gapiScript:"https://apis.google.com/js/api.js",recaptchaV2Script:"https://www.google.com/recaptcha/api.js",recaptchaEnterpriseScript:"https://www.google.com/recaptcha/enterprise.js?render="});va("Browser");var Gr="@firebase/installations",dn="0.6.9";var Kr=1e4,Jr=`w:${dn}`,Yr="FIS_v2",ba="https://firebaseinstallations.googleapis.com/v1",Aa=60*60*1e3,Sa="installations",Ra="Installations";var Oa={"missing-app-config-values":'Missing App configuration value: "{$valueName}"',"not-registered":"Firebase Installation is not registered.","installation-not-found":"Firebase Installation not found.","request-failed":'{$requestName} request failed with error "{$serverCode} {$serverStatus}: {$serverMessage}"',"app-offline":"Could not process request. Application offline.","delete-pending-registration":"Can't delete installation while there is a pending registration request."},z=new y(Sa,Ra,Oa);function Xr(t){return t instanceof I&&t.code.includes("request-failed")}function Qr({projectId:t}){return`${ba}/projects/${t}/installations`}function Zr(t){return{token:t.token,requestStatus:2,expiresIn:Pa(t.expiresIn),creationTime:Date.now()}}async function ei(t,e){let r=(await e.json()).error;return z.create("request-failed",{requestName:t,serverCode:r.code,serverMessage:r.message,serverStatus:r.status})}function ti({apiKey:t}){return new Headers({"Content-Type":"application/json",Accept:"application/json","x-goog-api-key":t})}function ka(t,{refreshToken:e}){let n=ti(t);return n.append("Authorization",Ca(e)),n}async function ni(t){let e=await t();return e.status>=500&&e.status<600?t():e}function Pa(t){return Number(t.replace("s","000"))}function Ca(t){return`${Yr} ${t}`}async function Na({appConfig:t,heartbeatServiceProvider:e},{fid:n}){let r=Qr(t),i=ti(t),s=e.getImmediate({optional:!0});if(s){let u=await s.getHeartbeatsHeader();u&&i.append("x-firebase-client",u)}let o={fid:n,authVersion:Yr,appId:t.appId,sdkVersion:Jr},a={method:"POST",headers:i,body:JSON.stringify(o)},c=await ni(()=>fetch(r,a));if(c.ok){let u=await c.json();return{fid:u.fid||n,registrationStatus:2,refreshToken:u.refreshToken,authToken:Zr(u.authToken)}}else throw await ei("Create Installation",c)}function ri(t){return new Promise(e=>{setTimeout(e,t)})}function Da(t){return btoa(String.fromCharCode(...t)).replace(/\+/g,"-").replace(/\//g,"_")}var La=/^[cdef][\w-]{21}$/,ln="";function Ma(){try{let t=new Uint8Array(17);(self.crypto||self.msCrypto).getRandomValues(t),t[0]=112+t[0]%16;let n=Ua(t);return La.test(n)?n:ln}catch{return ln}}function Ua(t){return Da(t).substr(0,22)}function it(t){return`${t.appName}!${t.appId}`}var ii=new Map;function si(t,e){let n=it(t);oi(n,e),xa(n,e)}function oi(t,e){let n=ii.get(t);if(n)for(let r of n)r(e)}function xa(t,e){let n=Fa();n&&n.postMessage({key:t,fid:e}),Va()}var q=null;function Fa(){return!q&&"BroadcastChannel"in self&&(q=new BroadcastChannel("[Firebase] FID Change"),q.onmessage=t=>{oi(t.data.key,t.data.fid)}),q}function Va(){ii.size===0&&q&&(q.close(),q=null)}var ja="firebase-installations-database",Ha=1,G="firebase-installations-store",cn=null;function hn(){return cn||(cn=be(ja,Ha,{upgrade:(t,e)=>{switch(e){case 0:t.createObjectStore(G)}}})),cn}async function rt(t,e){let n=it(t),i=(await hn()).transaction(G,"readwrite"),s=i.objectStore(G),o=await s.get(n);return await s.put(e,n),await i.done,(!o||o.fid!==e.fid)&&si(t,e.fid),e}async function ai(t){let e=it(t),r=(await hn()).transaction(G,"readwrite");await r.objectStore(G).delete(e),await r.done}async function st(t,e){let n=it(t),i=(await hn()).transaction(G,"readwrite"),s=i.objectStore(G),o=await s.get(n),a=e(o);return a===void 0?await s.delete(n):await s.put(a,n),await i.done,a&&(!o||o.fid!==a.fid)&&si(t,a.fid),a}async function fn(t){let e,n=await st(t.appConfig,r=>{let i=Wa(r),s=Ba(t,i);return e=s.registrationPromise,s.installationEntry});return n.fid===ln?{installationEntry:await e}:{installationEntry:n,registrationPromise:e}}function Wa(t){let e=t||{fid:Ma(),registrationStatus:0};return ci(e)}function Ba(t,e){if(e.registrationStatus===0){if(!navigator.onLine){let i=Promise.reject(z.create("app-offline"));return{installationEntry:e,registrationPromise:i}}let n={fid:e.fid,registrationStatus:1,registrationTime:Date.now()},r=$a(t,n);return{installationEntry:n,registrationPromise:r}}else return e.registrationStatus===1?{installationEntry:e,registrationPromise:qa(t)}:{installationEntry:e}}async function $a(t,e){try{let n=await Na(t,e);return rt(t.appConfig,n)}catch(n){throw Xr(n)&&n.customData.serverCode===409?await ai(t.appConfig):await rt(t.appConfig,{fid:e.fid,registrationStatus:0}),n}}async function qa(t){let e=await qr(t.appConfig);for(;e.registrationStatus===1;)await ri(100),e=await qr(t.appConfig);if(e.registrationStatus===0){let{installationEntry:n,registrationPromise:r}=await fn(t);return r||n}return e}function qr(t){return st(t,e=>{if(!e)throw z.create("installation-not-found");return ci(e)})}function ci(t){return za(t)?{fid:t.fid,registrationStatus:0}:t}function za(t){return t.registrationStatus===1&&t.registrationTime+Kr<Date.now()}async function Ga({appConfig:t,heartbeatServiceProvider:e},n){let r=Ka(t,n),i=ka(t,n),s=e.getImmediate({optional:!0});if(s){let u=await s.getHeartbeatsHeader();u&&i.append("x-firebase-client",u)}let o={installation:{sdkVersion:Jr,appId:t.appId}},a={method:"POST",headers:i,body:JSON.stringify(o)},c=await ni(()=>fetch(r,a));if(c.ok){let u=await c.json();return Zr(u)}else throw await ei("Generate Auth Token",c)}function Ka(t,{fid:e}){return`${Qr(t)}/${e}/authTokens:generate`}async function pn(t,e=!1){let n,r=await st(t.appConfig,s=>{if(!ui(s))throw z.create("not-registered");let o=s.authToken;if(!e&&Xa(o))return s;if(o.requestStatus===1)return n=Ja(t,e),s;{if(!navigator.onLine)throw z.create("app-offline");let a=Za(s);return n=Ya(t,a),a}});return n?await n:r.authToken}async function Ja(t,e){let n=await zr(t.appConfig);for(;n.authToken.requestStatus===1;)await ri(100),n=await zr(t.appConfig);let r=n.authToken;return r.requestStatus===0?pn(t,e):r}function zr(t){return st(t,e=>{if(!ui(e))throw z.create("not-registered");let n=e.authToken;return ec(n)?Object.assign(Object.assign({},e),{authToken:{requestStatus:0}}):e})}async function Ya(t,e){try{let n=await Ga(t,e),r=Object.assign(Object.assign({},e),{authToken:n});return await rt(t.appConfig,r),n}catch(n){if(Xr(n)&&(n.customData.serverCode===401||n.customData.serverCode===404))await ai(t.appConfig);else{let r=Object.assign(Object.assign({},e),{authToken:{requestStatus:0}});await rt(t.appConfig,r)}throw n}}function ui(t){return t!==void 0&&t.registrationStatus===2}function Xa(t){return t.requestStatus===2&&!Qa(t)}function Qa(t){let e=Date.now();return e<t.creationTime||t.creationTime+t.expiresIn<e+Aa}function Za(t){let e={requestStatus:1,requestTime:Date.now()};return Object.assign(Object.assign({},t),{authToken:e})}function ec(t){return t.requestStatus===1&&t.requestTime+Kr<Date.now()}async function tc(t){let e=t,{installationEntry:n,registrationPromise:r}=await fn(e);return r?r.catch(console.error):pn(e).catch(console.error),n.fid}async function mn(t,e=!1){let n=t;return await nc(n),(await pn(n,e)).token}async function nc(t){let{registrationPromise:e}=await fn(t);e&&await e}function li(t=Se()){return x(t,"installations").getImmediate()}function rc(t){if(!t||!t.options)throw un("App Configuration");if(!t.name)throw un("App Name");let e=["projectId","apiKey","appId"];for(let n of e)if(!t.options[n])throw un(n);return{appName:t.name,projectId:t.options.projectId,apiKey:t.options.apiKey,appId:t.options.appId}}function un(t){return z.create("missing-app-config-values",{valueName:t})}var di="installations",ic="installations-internal",sc=t=>{let e=t.getProvider("app").getImmediate(),n=rc(e),r=x(e,"heartbeat");return{app:e,appConfig:n,heartbeatServiceProvider:r,_delete:()=>Promise.resolve()}},oc=t=>{let e=t.getProvider("app").getImmediate(),n=x(e,di).getImmediate();return{getId:()=>tc(n),getToken:i=>mn(n,i)}};function ac(){P(new v(di,sc,"PUBLIC")),P(new v(ic,oc,"PRIVATE"))}ac();E(Gr,dn);E(Gr,dn,"esm2017");var K={apiKey:"x",authDomain:"",projectId:"",storageBucket:"",messagingSenderId:"",appId:"",measurementId:""};self.addEventListener("install",()=>{(!K||!K.apiKey||K.apiKey==="")&&console.warn("Warning - Firebase config not provided. Proxying will not be enabled"),console.log(`Initialised service worker. Project: ${K.projectId}`)});function cc(t){let e=t.split("/"),n=e[0],r=e[2];return n+"//"+r}self.addEventListener("fetch",t=>{let e=t;if(self.location.origin===cc(e.request.url)&&(self.location.protocol==="https:"||self.location.hostname==="localhost")){e.respondWith(uc(e.request));return}});async function uc(t){if(K){let e=Nt(K),n=an(e),r=li(e),i=new Headers(t.headers),[s,o]=await Promise.all([lc(n),mn(r)]);i.append("Firebase-Instance-ID-Token",o),s&&i.append("Authorization",`Bearer ${s}`);let a=new Request(t,{headers:i});return await fetch(a)}return console.warn("No Firebase config found. Headers are not being injected."),await fetch(t)}async function lc(t){if(await t.authStateReady(),!!t.currentUser)return await tn(t.currentUser)}})();
/*! Bundled license information:

@firebase/util/dist/index.esm2017.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/util/dist/index.esm2017.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/util/dist/index.esm2017.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/util/dist/index.esm2017.js:
  (**
   * @license
   * Copyright 2022 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/util/dist/index.esm2017.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
  (**
   * @license
   * Copyright 2021 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/util/dist/index.esm2017.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/util/dist/index.esm2017.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/util/dist/index.esm2017.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/util/dist/index.esm2017.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/util/dist/index.esm2017.js:
  (**
   * @license
   * Copyright 2022 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/util/dist/index.esm2017.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/util/dist/index.esm2017.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/util/dist/index.esm2017.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/util/dist/index.esm2017.js:
  (**
   * @license
   * Copyright 2022 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/util/dist/index.esm2017.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/util/dist/index.esm2017.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/util/dist/index.esm2017.js:
  (**
   * @license
   * Copyright 2021 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/component/dist/esm/index.esm2017.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/logger/dist/esm/index.esm2017.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/app/dist/esm/index.esm2017.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/app/dist/esm/index.esm2017.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
  (**
   * @license
   * Copyright 2023 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/app/dist/esm/index.esm2017.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/app/dist/esm/index.esm2017.js:
  (**
   * @license
   * Copyright 2021 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

firebase/app/dist/esm/index.esm.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2021 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
  (**
   * @license
   * Copyright 2022 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
  (**
   * @license
   * Copyright 2023 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
  (**
   * @license
   * Copyright 2020 Google LLC.
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
  (**
   * @license
   * Copyright 2021 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/auth/dist/esm2017/index-68602d24.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
  (**
   * @license
   * Copyright 2020 Google LLC.
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
  (**
   * @license
   * Copyright 2021 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/installations/dist/esm/index.esm2017.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/installations/dist/esm/index.esm2017.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/installations/dist/esm/index.esm2017.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/installations/dist/esm/index.esm2017.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)

@firebase/installations/dist/esm/index.esm2017.js:
  (**
   * @license
   * Copyright 2020 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
  (**
   * @license
   * Copyright 2019 Google LLC
   *
   * Licensed under the Apache License, Version 2.0 (the "License");
   * you may not use this file except in compliance with the License.
   * You may obtain a copy of the License at
   *
   *   http://www.apache.org/licenses/LICENSE-2.0
   *
   * Unless required by applicable law or agreed to in writing, software
   * distributed under the License is distributed on an "AS IS" BASIS,
   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   * See the License for the specific language governing permissions and
   * limitations under the License.
   *)
*/

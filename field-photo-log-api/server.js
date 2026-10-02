import express from "express";
import cors from "cors";
import crypto from "crypto";

const app = express();
const PORT = process.env.PORT || 10000;
const FRONTEND_URL = process.env.FRONTEND_URL || "https://field-photo-log.onrender.com";
const PROCORE_CLIENT_ID = process.env.PROCORE_CLIENT_ID || "";
const PROCORE_CLIENT_SECRET = process.env.PROCORE_CLIENT_SECRET || "";
const PROCORE_REDIRECT_URI = process.env.PROCORE_REDIRECT_URI || "";
const SESSION_SECRET = process.env.SESSION_SECRET || "change-me";

const AUTH_BASE = "https://login.procore.com";
const API_BASE = "https://api.procore.com";

app.use(cors({ origin: FRONTEND_URL, credentials: true }));
app.use(express.json({ limit: "2mb" }));

const sessions = new Map();

function parseCookies(req) {
  const raw = req.headers.cookie || "";
  return Object.fromEntries(raw.split(";").filter(Boolean).map(v => {
    const i = v.indexOf("=");
    return [decodeURIComponent(v.slice(0,i).trim()), decodeURIComponent(v.slice(i+1).trim())];
  }));
}
function sign(value) {
  return crypto.createHmac("sha256", SESSION_SECRET).update(value).digest("hex");
}
function getSession(req, res) {
  const cookies = parseCookies(req);
  let sid = cookies.fpl_sid;
  let valid = false;
  if (sid && sid.includes(".")) {
    const [id,sig] = sid.split(".");
    const expected = sign(id);
    valid = sig && crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected));
    if (valid) sid = id;
  }
  if (!valid) {
    sid = crypto.randomBytes(24).toString("hex");
    const signed = sid + "." + sign(sid);
    res.setHeader("Set-Cookie", "fpl_sid="+encodeURIComponent(signed)+"; Path=/; HttpOnly; Secure; SameSite=None; Max-Age=2592000");
  }
  if (!sessions.has(sid)) sessions.set(sid, {});
  return sessions.get(sid);
}
function configured() {
  return Boolean(PROCORE_CLIENT_ID && PROCORE_CLIENT_SECRET && PROCORE_REDIRECT_URI);
}
async function procoreFetch(path, token, opts={}) {
  return fetch(API_BASE + path, {
    ...opts,
    headers: {
      ...(opts.headers || {}),
      Authorization: "Bearer " + token
    }
  });
}
async function refreshIfNeeded(session) {
  if (!session.token) return false;
  const expiresAt = session.token.created_at * 1000 + session.token.expires_in * 1000 - 60000;
  if (Date.now() < expiresAt) return true;
  if (!session.token.refresh_token || !configured()) return false;
  const body = new URLSearchParams({
    grant_type:"refresh_token",
    client_id:PROCORE_CLIENT_ID,
    client_secret:PROCORE_CLIENT_SECRET,
    refresh_token:session.token.refresh_token,
    redirect_uri:PROCORE_REDIRECT_URI
  });
  const r = await fetch(AUTH_BASE+"/oauth/token",{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body});
  if (!r.ok) { session.token = null; return false; }
  session.token = await r.json();
  return true;
}

app.get("/health",(req,res)=>res.json({ok:true,configured:configured()}));

app.get("/api/procore/config",(req,res)=>{
  getSession(req,res);
  res.json({configured:configured(),redirectUri:PROCORE_REDIRECT_URI || null});
});

app.get("/api/procore/status", async (req,res)=>{
  const session=getSession(req,res);
  if (!session.token) return res.json({connected:false,configured:configured()});
  try {
    if (!(await refreshIfNeeded(session))) return res.json({connected:false,configured:configured()});
    const r=await procoreFetch("/rest/v1.0/me",session.token.access_token);
    if (!r.ok) return res.json({connected:false,configured:configured()});
    const user=await r.json();
    res.json({connected:true,configured:configured(),user:{id:user.id,name:user.name,login:user.login}});
  } catch(e) {
    res.status(500).json({connected:false,error:"Unable to verify Procore connection"});
  }
});

app.get("/auth/procore",(req,res)=>{
  const session=getSession(req,res);
  if (!configured()) {
    return res.status(503).send("Procore OAuth is not configured yet. Add PROCORE_CLIENT_ID, PROCORE_CLIENT_SECRET, and PROCORE_REDIRECT_URI in Render.");
  }
  const state=crypto.randomBytes(24).toString("hex");
  session.oauthState=state;
  const url=new URL(AUTH_BASE+"/oauth/authorize");
  url.searchParams.set("client_id",PROCORE_CLIENT_ID);
  url.searchParams.set("response_type","code");
  url.searchParams.set("redirect_uri",PROCORE_REDIRECT_URI);
  url.searchParams.set("state",state);
  res.redirect(url.toString());
});

app.get("/auth/procore/callback", async (req,res)=>{
  const session=getSession(req,res);
  const {code,state,error}=req.query;
  if (error) return res.redirect(FRONTEND_URL+"/?procore=error");
  if (!code || !state || state !== session.oauthState) return res.status(400).send("Invalid Procore OAuth callback.");
  try {
    const body=new URLSearchParams({
      grant_type:"authorization_code",
      client_id:PROCORE_CLIENT_ID,
      client_secret:PROCORE_CLIENT_SECRET,
      code:String(code),
      redirect_uri:PROCORE_REDIRECT_URI
    });
    const r=await fetch(AUTH_BASE+"/oauth/token",{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body});
    const data=await r.json();
    if (!r.ok) return res.status(400).send("Procore token exchange failed.");
    session.token=data;
    delete session.oauthState;
    res.redirect(FRONTEND_URL+"/?procore=connected");
  } catch(e) {
    res.status(500).send("Procore connection failed.");
  }
});

app.post("/api/procore/disconnect", async (req,res)=>{
  const session=getSession(req,res);
  try {
    if (session.token?.access_token && configured()) {
      const body=new URLSearchParams({
        token:session.token.access_token,
        client_id:PROCORE_CLIENT_ID,
        client_secret:PROCORE_CLIENT_SECRET
      });
      await fetch(AUTH_BASE+"/oauth/revoke",{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body});
    }
  } catch {}
  session.token=null;
  res.json({ok:true});
});

app.listen(PORT,()=>console.log("Field Photo Log API listening on "+PORT));

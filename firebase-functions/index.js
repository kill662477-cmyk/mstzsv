"use strict";

const {onCall, HttpsError} = require("firebase-functions/v2/https");
const admin = require("firebase-admin");

admin.initializeApp();
const db = admin.firestore();

const COLLECTION = "monstarz_rankings";
const SOOP_STATION_INFO_URL = "https://openapi.sooplive.com/user/stationinfo";

function cleanText(value, fallback, max = 60) {
  const text = String(value || fallback || "").trim();
  return text.slice(0, max) || String(fallback || "SOOP").slice(0, max);
}

function cleanNumber(value, min = 0, max = 999999999) {
  const n = Math.floor(Number(value) || 0);
  return Math.max(min, Math.min(max, n));
}

async function getSoopProfile(accessToken) {
  if (!accessToken || typeof accessToken !== "string") {
    throw new HttpsError("unauthenticated", "SOOP login is required.");
  }

  const body = new URLSearchParams({access_token: accessToken});
  const response = await fetch(SOOP_STATION_INFO_URL, {
    method: "POST",
    headers: {"Content-Type": "application/x-www-form-urlencoded"},
    body,
  });

  let json = null;
  try {
    json = await response.json();
  } catch (error) {
    throw new HttpsError("unauthenticated", "SOOP profile response was not valid JSON.");
  }

  const data = json && json.data ? json.data : {};
  if (!response.ok || json.result !== 1 || !data.user_nick) {
    throw new HttpsError("unauthenticated", "SOOP access token could not be verified.");
  }

  return {
    nick: cleanText(data.user_nick, "SOOP", 40),
    stationName: cleanText(data.station_name || data.user_id || data.user_nick, data.user_nick, 80),
  };
}

exports.submitRanking = onCall({region: "asia-northeast3", cors: true}, async (request) => {
  const input = request.data || {};
  const run = input.run || {};
  const profile = await getSoopProfile(input.soopAccessToken);

  const score = cleanNumber(run.score);
  if (score <= 0) {
    throw new HttpsError("failed-precondition", "Only ENDLESS records with kills can be ranked.");
  }

  const payload = {
    nick: profile.nick,
    stationName: profile.stationName,
    score,
    endlessKills: cleanNumber(run.endlessKills),
    kills: cleanNumber(run.kills),
    stage: cleanNumber(run.stage, 1, 3),
    level: cleanNumber(run.level, 1, 999),
    time: cleanNumber(run.time),
    charId: cleanText(run.charId, "RUN", 20),
    charKo: cleanText(run.charKo, "", 40),
    race: cleanText(run.race, "", 16),
    updatedAt: admin.firestore.FieldValue.serverTimestamp(),
  };

  const docId = Buffer.from(profile.stationName, "utf8").toString("base64url").slice(0, 120);
  const ref = db.collection(COLLECTION).doc(docId);
  let updated = false;

  await db.runTransaction(async (tx) => {
    const snap = await tx.get(ref);
    const oldScore = snap.exists ? cleanNumber(snap.data().score) : 0;
    if (score > oldScore) {
      tx.set(ref, {
        ...payload,
        createdAt: snap.exists ? snap.data().createdAt || admin.firestore.FieldValue.serverTimestamp() : admin.firestore.FieldValue.serverTimestamp(),
      }, {merge: true});
      updated = true;
    }
  });

  const finalSnap = await ref.get();
  const finalScore = finalSnap.exists ? cleanNumber(finalSnap.data().score) : score;
  return {ok: true, updated, nick: profile.nick, score: finalScore};
});

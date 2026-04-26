import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";

// Your Firebase web configuration
// (Found in Firebase Console -> Project Settings -> General -> Web Apps)
const firebaseConfig = {
  apiKey: "AIzaSyA4xXld5oqA0roPTcRVHpGavmZ_ux6-q_Q",
  authDomain: "uscout-db.firebaseapp.com",
  projectId: "uscout-db",
  storageBucket: "uscout-db.firebasestorage.app",
  messagingSenderId: "1068689947002",
  appId: "1:1068689947002:web:1a7e49ca7d18ac841cbec3"
};

const app = initializeApp(firebaseConfig);
export const db = getFirestore(app);
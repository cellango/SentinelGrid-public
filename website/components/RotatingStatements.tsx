"use client";

import { useEffect, useState } from "react";

const STATEMENTS = [
  // Original 7 statements
  "From first login to first alert in under a day.",
  "Security outcomes, not SIEM dashboards.",
  "Security that scales without hiring.",
  "Alerts explained in plain English, mapped to NIST.",
  "Your stack, our AI SOC in a box.",
  "SSO without a separate SSO bill.",
  "One platform. One bill. One security team.",
  
  // 10 new engaging alarm statements
  "We'll spot suspicious sign-ins before they become account takeovers.",
  "When someone reports phishing, we hunt down every copy and clean it up.",
  "We'll detect phishing campaigns and kill them before people start clicking.",
  "We catch malware on your endpoints early and walk you through the fix.",
  "If ransomware tries to start, we'll slam the brakes and guide you through recovery.",
  "We'll warn you the moment cloud storage gets exposed to the internet.",
  "We'll alert you anytime someone quietly becomes an admin.",
  "We'll flag password attacks so you can block bad actors fast.",
  "We'll spotlight unusual data transfers before they become breaches.",
  "Lost laptop? We'll treat it as a security event and shut down access fast.",
];

export function RotatingStatements() {
  const [index, setIndex] = useState(0);
  const [fade, setFade] = useState(true);

  useEffect(() => {
    const id = setInterval(() => {
      setFade(false);
      setTimeout(() => {
        setIndex((prev) => (prev + 1) % STATEMENTS.length);
        setFade(true);
      }, 300);
    }, 3500); // change every 3.5s

    return () => clearInterval(id);
  }, []);

  return (
    <p
      aria-live="polite"
      className={`text-sm md:text-base text-slate-300 mt-3 transition-opacity duration-500 ${
        fade ? "opacity-100" : "opacity-0"
      }`}
    >
      {STATEMENTS[index]}
    </p>
  );
}


"use client";

import { useEffect, useState } from "react";

const STATEMENTS = [
  "From first login to first alert in under a day.",
  "Security outcomes, not dashboards and acronyms.",
  "Security that scales without hiring.",
  "Alerts explained in plain English, mapped to NIST.",
  "Your stack, our AI SOC in a box.",
  "SSO without a separate SSO bill.",
  "One platform. One bill. One security team.",
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

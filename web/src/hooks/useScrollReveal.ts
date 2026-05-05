"use client";

import { useEffect } from "react";
import { useReducedMotion } from "./useReducedMotion";

export function useScrollReveal(selector = ".reveal") {
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    if (reducedMotion) {
      const elements = document.querySelectorAll(selector);
      for (const el of elements) {
        el.classList.add("revealed");
      }
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("revealed");
            observer.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.1, rootMargin: "0px 0px -40px 0px" },
    );

    const elements = document.querySelectorAll(selector);
    for (const el of elements) {
      observer.observe(el);
    }

    return () => observer.disconnect();
  }, [selector, reducedMotion]);
}

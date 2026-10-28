"use client";

import { useEffect } from "react";
import Gajju from "@/components/Gajju";

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => { console.error(error); }, [error]);
  return (
    <div className="mx-auto flex max-w-md flex-col items-center px-6 py-16 text-center">
      <Gajju state="error" size={150} />
      <h1 className="mt-4 text-2xl font-extrabold">Something went wrong · ఏదో తప్పు జరిగింది</h1>
      <p className="mt-2 text-ink-2">Gajju dozed off. Please try again.</p>
      <button onClick={reset} className="mt-6 inline-flex min-h-12 items-center rounded-2xl bg-peacock px-6 font-semibold text-white dark:text-[#06242b]">
        Try again · మళ్లీ ప్రయత్నించండి
      </button>
    </div>
  );
}

import Link from "next/link";
import Gajju from "@/components/Gajju";

export default function NotFound() {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center px-6 py-16 text-center">
      <Gajju state="unsure" size={150} />
      <h1 className="mt-4 text-2xl font-extrabold">Page not found · పేజీ దొరకలేదు</h1>
      <p className="mt-2 text-ink-2">Gajju looked everywhere but this page isn&apos;t here.</p>
      <Link href="/" className="mt-6 inline-flex min-h-12 items-center rounded-2xl bg-peacock px-6 font-semibold text-white dark:text-[#06242b]">
        Go to chat · చాట్‌కు వెళ్లండి
      </Link>
    </div>
  );
}

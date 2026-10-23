import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { POSTS, formatDate } from "@/lib/posts";

export const metadata: Metadata = {
  title: "Blog",
  description: "Notes, guides and updates from the Tarkbot project.",
  alternates: { canonical: "/blog" },
};

export default function BlogPage() {
  return (
    <>
      <section className="relative isolate overflow-hidden">
        <Image
          src="/blog/4608057-escape-from-tarkov-tips-map-knowledge.webp"
          alt=""
          fill
          priority
          sizes="100vw"
          className="-z-10 object-cover opacity-40"
        />
        <div className="absolute inset-0 -z-10 bg-gradient-to-b from-base/40 to-base" />
        <div className="mx-auto max-w-5xl px-6">
          <header className="flex items-center justify-between py-4">
            <Link href="/" className="text-lg font-semibold tracking-[0.2em] sm:tracking-[0.3em] uppercase">
              Tarkbot
            </Link>
            <Link href="/" className="text-sm text-ink-dim hover:text-ink transition-colors">
              Home
            </Link>
          </header>
          <div className="py-20 sm:py-28">
            <p className="text-xs uppercase tracking-[0.2em] text-ink-dim">Tarkbot blog</p>
            <h1 className="mt-6 text-5xl sm:text-7xl font-light leading-[0.95] tracking-tight">
              Field notes
            </h1>
            <p className="mt-6 max-w-2xl text-lg text-ink-dim leading-relaxed">
              Guides, updates and lessons from building a bot that plays the boring parts of Tarkov.
            </p>
          </div>
        </div>
      </section>

      <main className="flex-1 mx-auto w-full max-w-5xl px-6 pb-20">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {POSTS.map((post, i) => {
            // The newest post is a wide featured card. The rest fill a 3-column
            // grid on desktop; on tablet's 2 columns the last one goes full width
            // when it would otherwise sit alone.
            const featured = i === 0;
            const lastAlone = i === POSTS.length - 1 && (POSTS.length - 1) % 2 === 1;
            return (
            <Link
              key={post.slug}
              href={`/blog/${post.slug}`}
              className={`glass group flex flex-col overflow-hidden hover:border-ink-faint transition-colors ${
                featured ? "sm:col-span-2 lg:col-span-3 lg:flex-row" : lastAlone ? "sm:col-span-2 lg:col-span-1" : ""
              }`}
            >
              <div className={`relative aspect-video overflow-hidden ${featured ? "sm:aspect-[21/9] lg:aspect-auto lg:w-3/5 lg:min-h-80" : lastAlone ? "sm:aspect-[21/9] lg:aspect-video" : ""}`}>
                <Image
                  src={post.image}
                  alt=""
                  fill
                  priority={featured}
                  sizes={featured ? "(min-width: 1024px) 600px, 100vw" : lastAlone ? "(min-width: 1024px) 320px, 100vw" : "(min-width: 1024px) 320px, (min-width: 640px) 50vw, 100vw"}
                  className="object-cover transition-transform duration-500 group-hover:scale-105"
                />
              </div>
              <div className={`flex flex-1 flex-col p-5 ${featured ? "lg:p-8 lg:justify-center" : ""}`}>
                <time dateTime={post.date} className="text-xs uppercase tracking-[0.15em] text-ink-dim">
                  {formatDate(post.date)}
                </time>
                <h2 className={`mt-3 leading-tight ${featured ? "text-2xl lg:text-3xl font-light" : "text-xl"}`}>{post.title}</h2>
                <p className="mt-3 text-sm text-ink-dim leading-relaxed">{post.excerpt}</p>
                <span className={`pt-5 text-xs uppercase tracking-[0.15em] text-ink-dim group-hover:text-ink ${featured ? "lg:mt-4" : "mt-auto"}`}>
                  Read post →
                </span>
              </div>
            </Link>
            );
          })}
        </div>
      </main>
    </>
  );
}

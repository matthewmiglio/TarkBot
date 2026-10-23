import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { POSTS, formatDate } from "@/lib/posts";

type Props = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return POSTS.map(({ slug }) => ({ slug }));
}

export const dynamicParams = false;

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const post = POSTS.find((p) => p.slug === slug);
  if (!post) return {};
  return {
    title: post.title,
    description: post.excerpt,
    alternates: { canonical: `/blog/${post.slug}` },
    openGraph: { type: "article", title: post.title, description: post.excerpt, images: [post.image] },
  };
}

export default async function PostPage({ params }: Props) {
  const { slug } = await params;
  const post = POSTS.find((p) => p.slug === slug);
  if (!post) notFound();

  return (
    <>
      <section className="relative isolate overflow-hidden">
        <Image src={post.image} alt="" fill priority sizes="100vw" className="-z-10 object-cover opacity-50" />
        <div className="absolute inset-0 -z-10 bg-gradient-to-b from-base/60 via-base/75 to-base" />
        <div className="mx-auto max-w-5xl xl:max-w-7xl px-6">
          <header className="flex items-center justify-between py-4">
            <Link href="/" className="text-lg font-semibold tracking-[0.2em] sm:tracking-[0.3em] uppercase">
              Tarkbot
            </Link>
            <Link href="/blog" className="text-sm xl:text-base text-ink-dim hover:text-ink transition-colors">
              ← All posts
            </Link>
          </header>
          <div className="max-w-3xl xl:max-w-5xl pt-24 pb-16 sm:pt-40 sm:pb-24">
            <time dateTime={post.date} className="text-xs uppercase tracking-[0.2em] text-ink-dim">
              {formatDate(post.date)}
            </time>
            <h1 className="mt-5 text-4xl sm:text-6xl xl:text-7xl font-light leading-[1.05] tracking-tight">{post.title}</h1>
            <p className="mt-6 text-lg xl:text-2xl text-ink-dim leading-relaxed">{post.excerpt}</p>
          </div>
        </div>
      </section>

      <main className="flex-1 mx-auto w-full max-w-5xl xl:max-w-7xl px-6 pb-24">
        <article className="max-w-3xl xl:max-w-5xl space-y-6 xl:space-y-8 text-lg xl:text-2xl text-ink-dim leading-relaxed">
          {post.body.map((para, i) =>
            para.startsWith("## ") ? (
              <h2 key={i} className="pt-6 text-2xl sm:text-3xl xl:text-4xl font-light tracking-tight text-ink">
                {para.slice(3)}
              </h2>
            ) : (
              <p key={i}>{para}</p>
            ),
          )}
        </article>
        {/* Links to the home page rather than straight to GitHub, so the dashboard's
            blog funnel sees the visitor reach the download page first. */}
        <aside className="glass mt-16 max-w-3xl xl:max-w-5xl p-6 sm:p-8 xl:p-10">
          <p className="text-lg xl:text-2xl leading-relaxed">{post.cta}</p>
          <Link
            href="/"
            className="mt-6 inline-block border border-edge px-6 py-3 text-sm uppercase tracking-[0.15em] hover:bg-plate-hot transition-colors"
          >
            Get Tarkbot, free →
          </Link>
        </aside>
        <div className="mt-16 h-px bg-line" />
        <Link href="/blog" className="mt-8 inline-block text-sm uppercase tracking-[0.15em] text-ink-dim hover:text-ink">
          ← Back to the blog
        </Link>
      </main>
    </>
  );
}

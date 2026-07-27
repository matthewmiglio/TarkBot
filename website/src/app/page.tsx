import { DownloadButton, DISCORD_URL, RELEASES_URL } from "./download-button";

const LOOP = [
  ["01", "Find the window", "Locates the Tarkov window through user32 and works in its coordinates. The game runs fullscreen, so screen coords are game coords."],
  ["02", "Pick an item", "Infers the inventory grid from the All / auto-sort buttons framing it, masks out empty slots, and picks something to sell. Scav case boxes are excluded, or used exclusively, your choice."],
  ["03", "Open the offer", "Clicks Add Offer, waits for a free offer slot, unticks 'select similar items' if the game ticked it."],
  ["04", "Read the price", "Crops the suggested price region and reads the digits. All of it or none of it, because a half-read price is a wrong price."],
  ["05", "Undercut", "Takes the better of 15% off and 2000 roubles off, so the flat cut wins on expensive loot and the percentage wins on cheap loot, and neither goes negative."],
  ["06", "List it", "Types the new price, clicks Place Offer, and goes back to step 2."],
];

const DOES = [
  "Sells from your stash or straight out of scav cases, whichever you pick.",
  "Reads Tarkov's own suggested price and undercuts it. No external price API.",
  "Waits for a free offer slot instead of failing when your offers are full.",
  "Stops mid-pass, not at the end of one, so Stop means stop.",
  "Live stats: passes, items listed, prices read, failures.",
  "Turns the state lamp red on a wrong screen instead of silently dying.",
  "Themeable control panel. Drop a PNG in the backgrounds folder and it shows up in the picker.",
];

const DOESNT = [
  "No memory reading, no injection, no packet work. It looks at pixels and moves your mouse.",
  "No raid automation. It does not aim, loot, heal or move your character.",
  "No account, no login, no licence key. The app itself phones nothing home.",
  "No price API, no market database, no external service of any kind.",
  "Not headless. It drives the real cursor, so the game window has to be up front.",
  "Windows only, and it wants the resolution the reference images were cut at.",
];

const TECH = [
  ["Template matching", "Every button is a cropped screenshot on disk. OpenCV matches those references against the live window at 0.9 confidence. Teaching it a new UI state is dropping another PNG in the folder."],
  ["Pixel-matched digits", "The price reader is not an OCR engine. Tarkov prints prices in a fixed bitmap font, so the crop gets cut into glyphs and each glyph is pixel-matched against a reference. A real OCR engine was tried first and read 999 as 666 at full confidence."],
  ["Brightness state reads", "Some elements only change colour, never shape. The flea taskbar icon inverts (mean channel 57 closed, 117 open) and Add Offer greys out (255 lit, 123 greyed), so those get read as thresholds rather than a second template."],
  ["Empty-slot masking", "Finding loot means knowing what an empty slot looks like. Every colour in the reference set is baked into a 256³ boolean cube at ±5 per channel, and anything matching it is not an item."],
];

function Rule() {
  return <div className="h-px bg-line" />;
}

export default function Page() {
  return (
    <main className="flex-1 mx-auto w-full max-w-5xl px-6">
      <header className="flex items-center justify-between py-4">
        <span className="text-lg font-semibold tracking-[0.3em] uppercase">
          Tarkbot
        </span>
        <nav className="flex items-center gap-6 text-sm text-ink-dim">
          <a href="#how" className="hover:text-ink transition-colors">How it works</a>
          <a href="#features" className="hover:text-ink transition-colors">Features</a>
          <a href={DISCORD_URL} target="_blank" rel="noopener noreferrer" className="hover:text-ink transition-colors">Discord</a>
        </nav>
      </header>
      <Rule />

      <section className="py-20 sm:py-28">
        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-ink-faint">
          <span className="size-2 rounded-full bg-running" />
          Free · Escape From Tarkov · Windows
        </div>
        <h1 className="mt-6 text-5xl sm:text-7xl font-light leading-[0.95] tracking-tight">
          It sells your loot
          <br />
          <span className="text-ink-dim">while you do something else.</span>
        </h1>
        <p className="mt-8 max-w-2xl text-lg text-ink-dim leading-relaxed">
          Tarkbot watches the Tarkov window, picks an item out of your stash,
          reads the suggested price off the screen, undercuts it and puts it on
          the flea market. Then it does it again. It reads pixels and moves your
          mouse, nothing else.
        </p>
        <div className="mt-10 flex flex-wrap items-center gap-4">
          <DownloadButton className="glass px-7 py-3 text-sm uppercase tracking-[0.15em] hover:bg-plate-hot transition-colors">
            Download
          </DownloadButton>
          <a
            href={DISCORD_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="px-7 py-3 text-sm uppercase tracking-[0.15em] text-ink-dim border border-line hover:text-ink hover:border-edge transition-colors"
          >
            Join the Discord
          </a>
          <span className="text-sm text-ink-faint">
            Builds on{" "}
            <a href={RELEASES_URL} target="_blank" rel="noopener noreferrer" className="underline underline-offset-4 hover:text-ink-dim">
              GitHub Releases
            </a>
          </span>
        </div>
      </section>

      <Rule />

      <section id="how" className="py-20">
        <h2 className="text-xs uppercase tracking-[0.25em] text-ink-faint">One pass</h2>
        <p className="mt-4 max-w-2xl text-ink-dim">
          A pass is six steps. The bot repeats it until you press Stop, and a
          pass that dies on the wrong screen is abandoned and restarted rather
          than taking the app down with it.
        </p>
        <ol className="mt-10 grid gap-px bg-line sm:grid-cols-2 lg:grid-cols-3">
          {LOOP.map(([n, title, body]) => (
            <li key={n} className="glass border-0 p-6">
              <span className="font-mono text-xs text-running">{n}</span>
              <h3 className="mt-3 text-lg">{title}</h3>
              <p className="mt-2 text-sm text-ink-dim leading-relaxed">{body}</p>
            </li>
          ))}
        </ol>
      </section>

      <Rule />

      <section className="py-20">
        <h2 className="text-xs uppercase tracking-[0.25em] text-ink-faint">Under the hood</h2>
        <div className="mt-10 grid gap-10 sm:grid-cols-2">
          {TECH.map(([title, body]) => (
            <div key={title}>
              <h3 className="text-lg">{title}</h3>
              <p className="mt-2 text-sm text-ink-dim leading-relaxed">{body}</p>
            </div>
          ))}
        </div>
        <p className="mt-10 max-w-3xl text-sm text-ink-faint leading-relaxed">
          Python, with pyautogui, opencv-python, numpy and pillow doing the work
          and a tkinter control panel on top. Everything else is standard
          library.
        </p>
      </section>

      <Rule />

      <section id="features" className="py-20 grid gap-12 sm:grid-cols-2">
        <div>
          <h2 className="text-xs uppercase tracking-[0.25em] text-running">What it does</h2>
          <ul className="mt-6 space-y-3">
            {DOES.map((item) => (
              <li key={item} className="flex gap-3 text-sm text-ink-dim leading-relaxed">
                <span className="mt-2 size-1 shrink-0 rounded-full bg-running" />
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h2 className="text-xs uppercase tracking-[0.25em] text-warning">What it doesn&apos;t</h2>
          <ul className="mt-6 space-y-3">
            {DOESNT.map((item) => (
              <li key={item} className="flex gap-3 text-sm text-ink-dim leading-relaxed">
                <span className="mt-2 size-1 shrink-0 rounded-full bg-warning" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </section>

      <Rule />

      <section className="py-20 sm:py-28 text-center">
        <h2 className="text-4xl sm:text-5xl font-light tracking-tight">
          It&apos;s free. Go get it.
        </h2>
        <p className="mt-5 text-ink-dim">
          No account, no key, no payment. Grab a build, unzip it, run it.
        </p>
        <div className="mt-10 flex flex-wrap justify-center gap-4">
          <DownloadButton className="glass px-7 py-3 text-sm uppercase tracking-[0.15em] hover:bg-plate-hot transition-colors">
            Download from GitHub
          </DownloadButton>
          <a
            href={DISCORD_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="px-7 py-3 text-sm uppercase tracking-[0.15em] text-ink-dim border border-line hover:text-ink hover:border-edge transition-colors"
          >
            Get help on Discord
          </a>
        </div>
      </section>

      <Rule />

      <footer className="py-8 flex flex-wrap items-center justify-between gap-4 text-xs text-ink-faint">
        <span>Tarkbot — free software, use at your own risk.</span>
        <span className="flex gap-5">
          <a href={RELEASES_URL} target="_blank" rel="noopener noreferrer" className="hover:text-ink-dim">Releases</a>
          <a href={DISCORD_URL} target="_blank" rel="noopener noreferrer" className="hover:text-ink-dim">Discord</a>
        </span>
      </footer>
    </main>
  );
}

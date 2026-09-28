import Link from 'next/link';
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  FileText,
  FolderOpen,
  LockKeyhole,
  MessageSquare,
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
} from 'lucide-react';

export default function HomePage() {
	return (
		<main className="min-h-screen overflow-hidden bg-[#f6f8f3] text-[#18251d]">
			<header className="relative z-10 mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8 lg:px-12">
				<Link href="/" aria-label="VaultPulse.AI home" className="flex items-center gap-2.5 font-semibold tracking-tight">
					<span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#183528] text-[#c8f27c]"><LockKeyhole size={18} /></span>
					<span>VaultPulse<span className="text-[#739c59]">.AI</span></span>
				</Link>
				<nav aria-label="Main navigation" className="hidden items-center gap-8 text-sm text-[#526158] md:flex">
					<a href="#workspace" className="transition hover:text-[#18251d]">Workspace</a>
					<a href="#capabilities" className="transition hover:text-[#18251d]">Capabilities</a>
					<a href="#privacy" className="transition hover:text-[#18251d]">Privacy</a>
				</nav>
				<div className="flex items-center gap-2 sm:gap-3">
					<Link href="/login" className="rounded-full px-3 py-2 text-sm font-medium text-[#526158] transition hover:text-[#18251d] sm:px-4">Sign in</Link>
					<Link href="/register" className="inline-flex items-center gap-2 rounded-full bg-[#183528] px-4 py-2.5 text-sm font-medium text-white transition hover:bg-[#244a37] sm:px-5">Get started <ArrowUpRight size={15} /></Link>
				</div>
			</header>

			<section id="workspace" className="relative px-5 pb-16 pt-14 text-center sm:px-8 sm:pt-20 lg:pb-24 lg:pt-24">
				<div className="pointer-events-none absolute left-1/2 top-0 -z-0 h-[620px] w-[min(1100px,100vw)] -translate-x-1/2 bg-[radial-gradient(ellipse_at_center,rgba(213,235,186,0.34),transparent_68%)]" />
				<div className="relative mx-auto max-w-4xl">
					<div className="mx-auto mb-7 flex w-fit items-center gap-2 rounded-full border border-[#dbe5d4] bg-white/80 px-3.5 py-1.5 text-xs font-medium text-[#526a52] shadow-sm shadow-[#183528]/5">
						<span className="h-1.5 w-1.5 rounded-full bg-[#83bd56]" /> A calmer way to find what you know
					</div>
					<h1 className="text-balance text-4xl font-semibold leading-[1.08] tracking-[-0.045em] sm:text-6xl lg:text-[76px]">
						Your knowledge, <span className="text-[#67994a]">in reach.</span>
					</h1>
					<p className="mx-auto mt-6 max-w-2xl text-pretty text-base leading-7 text-[#657269] sm:text-lg sm:leading-8">
						Bring your files and conversations together, then ask a thoughtful assistant to help you find the signal.
					</p>
					<div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
						<Link href="/register" className="inline-flex h-12 items-center justify-center gap-2 rounded-full bg-[#b8e978] px-6 text-sm font-semibold text-[#20351f] shadow-[0_5px_16px_rgba(124,166,79,0.2)] transition hover:bg-[#c7f28c]">Create your workspace <ArrowRight size={16} /></Link>
						<a href="#capabilities" className="inline-flex h-12 items-center justify-center rounded-full px-5 text-sm font-medium text-[#526158] transition hover:bg-white/70">Explore the workspace</a>
					</div>
				</div>

				<div className="relative mx-auto mt-14 max-w-6xl text-left sm:mt-20">
					<div className="absolute -inset-x-5 -bottom-8 -top-8 -z-0 rounded-[32px] bg-[#deebd2]/65 blur-2xl sm:-inset-x-10" />
					<div className="relative overflow-hidden rounded-[20px] border border-[#d7e0d3] bg-[#102219] shadow-[0_30px_90px_rgba(31,60,42,0.2)] sm:rounded-[24px]">
						<div className="flex h-12 items-center justify-between border-b border-white/[0.08] px-4 sm:px-6">
							<div className="flex items-center gap-2"><span className="h-2 w-2 rounded-full bg-[#b8e978]" /><span className="text-xs font-medium text-white/80">VaultPulse workspace</span></div>
							<div className="hidden items-center gap-1.5 text-[11px] text-white/45 sm:flex"><ShieldCheck size={13} /> Private by design</div>
						</div>
						<div className="grid min-h-[360px] grid-cols-1 md:grid-cols-[210px_minmax(0,1fr)] lg:grid-cols-[230px_minmax(0,1fr)]">
							<aside className="hidden border-r border-white/[0.08] p-4 md:block">
								<div className="mb-5 flex items-center gap-2 rounded-lg bg-white/[0.07] px-3 py-2 text-[11px] text-white/55"><Search size={13} /> Search your space</div>
								<p className="mb-2 px-2 text-[9px] font-semibold uppercase tracking-[0.12em] text-white/35">Your library</p>
								<div className="space-y-1 text-xs text-white/65">
									<div className="flex items-center gap-2 rounded-lg bg-[#b8e978]/10 px-2.5 py-2 text-[#d0f69c]"><FolderOpen size={14} /> All files <span className="ml-auto text-[10px] text-white/40">24</span></div>
									<div className="flex items-center gap-2 rounded-lg px-2.5 py-2"><MessageSquare size={14} /> Conversations</div>
									<div className="flex items-center gap-2 rounded-lg px-2.5 py-2"><Sparkles size={14} /> Saved insights</div>
								</div>
								<div className="mt-7 border-t border-white/[0.08] pt-4">
									<p className="mb-2 px-2 text-[9px] font-semibold uppercase tracking-[0.12em] text-white/35">Recent folders</p>
									<div className="space-y-2 px-2 text-[11px] text-white/55"><p>Product research</p><p>Team notes</p><p>Q3 planning</p></div>
								</div>
							</aside>
							<div className="grid min-w-0 grid-cols-1 lg:grid-cols-[1fr_0.9fr]">
								<div className="min-w-0 p-4 sm:p-6">
									<div className="mb-5 flex items-center justify-between gap-3">
										<div><p className="text-[10px] text-white/45">Tuesday, October 14</p><h2 className="mt-1 text-lg font-medium text-white sm:text-xl">Good morning, Alex</h2></div>
										<button type="button" className="flex shrink-0 items-center gap-1.5 rounded-lg bg-[#b8e978] px-3 py-2 text-[11px] font-semibold text-[#20351f]"><Upload size={13} /> Add files</button>
									</div>
									<div className="mb-3 flex items-center justify-between"><p className="text-[11px] font-medium text-white/80">Recently added</p><span className="text-[10px] text-white/40">View library <ArrowUpRight className="ml-0.5 inline" size={11} /></span></div>
									<div className="space-y-2">
										{[['Research synthesis.pdf', 'PDF · 2.4 MB · Added today'], ['Planning notes.docx', 'DOCX · 480 KB · Added yesterday'], ['Customer interviews.txt', 'TXT · 18 KB · Added Oct 10']].map(([name, meta]) => <div key={name} className="flex items-center gap-3 rounded-xl border border-white/[0.08] bg-white/[0.035] px-3 py-3"><span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#b8e978]/10 text-[#c8ef94]"><FileText size={15} /></span><span className="min-w-0 flex-1"><span className="block truncate text-[11px] font-medium text-white/85">{name}</span><span className="mt-0.5 block truncate text-[9px] text-white/40">{meta}</span></span><Check className="shrink-0 text-[#b8e978]" size={14} /></div>)}
									</div>
								</div>
								<div className="border-t border-white/[0.08] bg-[#0d1c14] p-4 sm:p-6 lg:border-l lg:border-t-0">
									<div className="mb-4 flex items-center gap-2"><span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#b8e978]/10 text-[#c8ef94]"><Sparkles size={14} /></span><span className="text-[11px] font-medium text-white/85">Ask your knowledge base</span></div>
									<div className="rounded-xl border border-white/[0.08] bg-white/[0.04] p-3.5">
										<p className="text-[11px] leading-5 text-white/75">What were the recurring themes in our latest customer interviews?</p>
										<div className="mt-4 border-t border-white/[0.08] pt-3">
											<p className="text-[10px] leading-5 text-white/65">Three themes appear across the notes: setup clarity, faster search, and better handoffs between teams.</p>
											<div className="mt-3 flex items-center gap-1.5 text-[9px] text-[#c8ef94]"><FileText size={11} /> Based on 4 files <ArrowUpRight size={10} /></div>
										</div>
									</div>
									<div className="mt-3 flex items-center justify-between rounded-lg border border-white/[0.08] px-3 py-2.5 text-[10px] text-white/35"><span>Ask about your files...</span><span className="flex h-5 w-5 items-center justify-center rounded-md bg-[#b8e978] text-[#20351f]"><ArrowRight size={11} /></span></div>
								</div>
							</div>
						</div>
					</div>
					<p className="mt-5 text-center text-xs text-[#748075]">A clear view of what matters, without the digging.</p>
				</div>
			</section>

			<section id="capabilities" className="border-y border-[#e2e9dc] bg-white/70 px-5 py-16 sm:px-8 lg:py-20">
				<div className="mx-auto max-w-6xl">
					<div className="max-w-2xl"><p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#70934f]">Made for your everyday work</p><h2 className="mt-3 text-3xl font-semibold leading-tight tracking-[-0.035em] sm:text-4xl">Less searching. More connecting the dots.</h2><p className="mt-4 max-w-xl text-sm leading-6 text-[#657269]">A focused space to bring scattered knowledge together and turn it into something useful.</p></div>
					<div className="mt-12 grid gap-8 border-t border-[#e2e9dc] pt-8 md:grid-cols-3 md:gap-10">
						<article><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#eaf3e2] text-[#4f7838]"><Search size={18} /></span><h3 className="mt-5 text-base font-semibold">Find the right detail</h3><p className="mt-2 text-sm leading-6 text-[#657269]">Search across the material you bring in and get to relevant context sooner.</p></article>
						<article><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#eaf3e2] text-[#4f7838]"><Sparkles size={18} /></span><h3 className="mt-5 text-base font-semibold">Ask with context</h3><p className="mt-2 text-sm leading-6 text-[#657269]">Explore questions in plain language and keep the source material close by.</p></article>
						<article id="privacy"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#eaf3e2] text-[#4f7838]"><ShieldCheck size={18} /></span><h3 className="mt-5 text-base font-semibold">Keep your space yours</h3><p className="mt-2 text-sm leading-6 text-[#657269]">Work in a private workspace designed to keep your information together.</p></article>
					</div>
				</div>
			</section>

			<section className="bg-[#173528] px-5 py-16 text-white sm:px-8 lg:py-20">
				<div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-7 sm:flex-row sm:items-center">
					<div><p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#c5e99c]">Your workspace starts here</p><h2 className="mt-3 max-w-xl text-3xl font-semibold leading-tight tracking-[-0.035em] sm:text-4xl">Bring your knowledge into focus.</h2></div>
					<Link href="/register" className="inline-flex h-12 shrink-0 items-center gap-2 rounded-full bg-[#b8e978] px-6 text-sm font-semibold text-[#20351f] transition hover:bg-[#c7f28c]">Create an account <ArrowRight size={16} /></Link>
				</div>
			</section>

			<footer className="mx-auto flex max-w-7xl flex-col gap-3 px-5 py-6 text-xs text-[#778278] sm:flex-row sm:items-center sm:justify-between sm:px-8 lg:px-12">
				<Link href="/" className="font-semibold text-[#405447]">VaultPulse.AI</Link><p>© 2026 VaultPulse.AI. A little more clarity for your day.</p>
			</footer>
		</main>
	);
}

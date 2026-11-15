"use client";
import Image from "next/image";
import Link from "next/link";
export default function Landing() {
  return <main className="min-h-screen bg-[#faf9f6] px-3 py-5 text-[#171d1c] sm:px-6 sm:py-8">
    <div className="mx-auto max-w-[1180px] overflow-hidden rounded-[26px] border border-[#eae9e5] bg-[#fffefc] shadow-[0_8px_35px_rgba(40,47,41,.07)]">
      <header className="flex items-center justify-between border-b border-[#eeedea] px-6 py-5 sm:px-12"><Link href="/" className="flex items-center gap-3 text-lg font-bold"><span className="rounded-full bg-[#326647] px-3 py-2 text-white">✦</span>Paperwork Navigator</Link><Link href="/login" className="text-sm font-semibold text-[#326647]">Enter Demo →</Link></header>
      <section className="px-6 pb-16 pt-14 sm:px-12 lg:px-14 lg:pt-20">
        <div className="grid items-center gap-6 md:grid-cols-[1.45fr_1fr]">
          <div><p className="mb-4 text-sm font-semibold uppercase tracking-widest text-[#397453]">UW · Post-Completion OPT</p><h1 className="text-[clamp(42px,5vw,68px)] font-bold leading-[1.07] tracking-[-.045em]">Settle in the U.S.<br/><span className="relative inline-block">step by step.<span className="absolute -bottom-1 left-0 -z-10 h-[10px] w-full -rotate-1 rounded-full bg-[#dfead9]"/></span></h1><p className="mt-7 max-w-[540px] text-lg leading-relaxed text-[#414948]">Understand your OPT steps, important dates, and who to contact — in one place.</p></div>
          <div className="mx-auto w-full max-w-[365px]"><Image src="/campus-illustration.png" alt="University campus illustration" width={309} height={340} priority className="h-auto w-full mix-blend-multiply" /></div>
        </div>
        <section className="mx-auto mt-10 max-w-[880px] rounded-[25px] border border-[#e9e8e4] bg-[#fffefc] px-6 py-7 shadow-[0_12px_34px_rgba(50,55,50,.055)] sm:px-9 sm:py-9">
          <h2 className="text-2xl font-bold">Let's plan your OPT journey</h2><p className="mt-2 text-[#65706e]">Designed for first-time UW F-1 students applying for post-completion OPT.</p>
          <Link href="/login" className="mt-6 block rounded-xl bg-[#336a48] px-6 py-4 text-center font-semibold text-white hover:bg-[#28583b]">Get Started →</Link>
          <p className="mt-3 text-xs text-gray-500">Demo only · No real email sign-in or backend data yet</p>
        </section>
        <div className="mt-16 grid gap-8 text-center md:grid-cols-3">{[{icon:"▤",title:"Personalized Plan",text:"See the right steps for your OPT stage."},{icon:"◷",title:"Important Dates",text:"Explore filing windows and planning milestones."},{icon:"✦",title:"Know Who to Ask",text:"Find official school and government sources."}].map(x=><div key={x.title} className="px-4"><div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-[#eef3e9] text-2xl text-[#336a48]">{x.icon}</div><h3 className="font-bold">{x.title}</h3><p className="mt-2 text-sm text-[#606a68]">{x.text}</p></div>)}</div>
      </section>
    </div>
  </main>;
}

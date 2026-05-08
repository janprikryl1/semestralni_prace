const pptxgen = require("pptxgenjs");

const pptx = new pptxgen();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "Jan Prikryl";
pptx.subject = "Software Architecture Document";
pptx.title = "Vyhledavani vzoru a technicke analyzy kryptomen";
pptx.company = "Semestralni projekt";
pptx.lang = "cs-CZ";
pptx.theme = {
  headFontFace: "Aptos Display",
  bodyFontFace: "Aptos",
  lang: "cs-CZ",
};
pptx.defineLayout({ name: "CUSTOM_WIDE", width: 13.333, height: 7.5 });
pptx.layout = "CUSTOM_WIDE";
pptx.margin = 0;

const C = {
  ink: "152236",
  muted: "607085",
  bg: "F6F8FB",
  paper: "FFFFFF",
  blue: "2563EB",
  cyan: "06B6D4",
  green: "16A34A",
  amber: "F59E0B",
  red: "DC2626",
  line: "D6DEE8",
  softBlue: "EAF2FF",
  softCyan: "E6F7FB",
  softGreen: "EAF8EF",
  softAmber: "FFF5DD",
};

const W = 13.333;
const H = 7.5;

function addBg(slide) {
  slide.background = { color: C.bg };
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 0,
    w: W,
    h: H,
    fill: { color: C.bg },
    line: { color: C.bg },
  });
}

function addFooter(slide, n) {
  slide.addText("Software Architecture Document", {
    x: 0.55,
    y: 7.03,
    w: 4.5,
    h: 0.22,
    fontFace: "Aptos",
    fontSize: 7.5,
    color: C.muted,
    margin: 0,
  });
  slide.addText(String(n).padStart(2, "0"), {
    x: 12.35,
    y: 7.0,
    w: 0.45,
    h: 0.25,
    fontFace: "Aptos",
    fontSize: 8,
    bold: true,
    color: C.muted,
    align: "right",
    margin: 0,
  });
}

function title(slide, text, subtitle) {
  slide.addText(text, {
    x: 0.7,
    y: 0.42,
    w: 8.8,
    h: 0.55,
    fontFace: "Aptos Display",
    fontSize: 25,
    bold: true,
    color: C.ink,
    margin: 0,
    breakLine: false,
    fit: "shrink",
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.72,
      y: 1.03,
      w: 8.6,
      h: 0.28,
      fontSize: 10.5,
      color: C.muted,
      margin: 0,
      fit: "shrink",
    });
  }
}

function sectionLabel(slide, text, x, y, color = C.blue) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w: 1.35,
    h: 0.29,
    rectRadius: 0.06,
    fill: { color },
    line: { color },
  });
  slide.addText(text.toUpperCase(), {
    x: x + 0.08,
    y: y + 0.055,
    w: 1.2,
    h: 0.14,
    fontSize: 6.5,
    color: "FFFFFF",
    bold: true,
    align: "center",
    margin: 0,
    breakLine: false,
    fit: "shrink",
  });
}

function pill(slide, text, x, y, w, color, fill) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h: 0.36,
    rectRadius: 0.08,
    fill: { color: fill },
    line: { color },
  });
  slide.addText(text, {
    x: x + 0.12,
    y: y + 0.08,
    w: w - 0.24,
    h: 0.14,
    fontSize: 8,
    bold: true,
    color,
    align: "center",
    margin: 0,
    fit: "shrink",
  });
}

function bulletList(slide, items, x, y, w, options = {}) {
  const fontSize = options.fontSize ?? 14;
  const gap = options.gap ?? 0.5;
  items.forEach((item, idx) => {
    const yy = y + idx * gap;
    slide.addShape(pptx.ShapeType.ellipse, {
      x,
      y: yy + 0.08,
      w: 0.09,
      h: 0.09,
      fill: { color: options.dotColor ?? C.blue },
      line: { color: options.dotColor ?? C.blue },
    });
    slide.addText(item, {
      x: x + 0.22,
      y: yy,
      w,
      h: 0.34,
      fontSize,
      color: options.color ?? C.ink,
      margin: 0,
      fit: "shrink",
      breakLine: false,
    });
  });
}

function card(slide, x, y, w, h, heading, body, accent, fill = C.paper) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    fill: { color: fill },
    line: { color: C.line, transparency: 5 },
  });
  slide.addShape(pptx.ShapeType.rect, {
    x,
    y,
    w: 0.08,
    h,
    fill: { color: accent },
    line: { color: accent },
  });
  slide.addText(heading, {
    x: x + 0.28,
    y: y + 0.22,
    w: w - 0.45,
    h: 0.28,
    fontSize: 13,
    bold: true,
    color: C.ink,
    margin: 0,
    fit: "shrink",
  });
  slide.addText(body, {
    x: x + 0.28,
    y: y + 0.65,
    w: w - 0.45,
    h: h - 0.82,
    fontSize: 9.5,
    color: C.muted,
    breakLine: false,
    margin: 0,
    fit: "shrink",
    valign: "mid",
  });
}

function step(slide, label, detail, x, y, w, color) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h: 0.94,
    rectRadius: 0.08,
    fill: { color: "FFFFFF" },
    line: { color: C.line },
  });
  slide.addText(label, {
    x: x + 0.15,
    y: y + 0.16,
    w: w - 0.3,
    h: 0.22,
    fontSize: 10.5,
    bold: true,
    color,
    margin: 0,
    align: "center",
    fit: "shrink",
  });
  slide.addText(detail, {
    x: x + 0.16,
    y: y + 0.48,
    w: w - 0.32,
    h: 0.22,
    fontSize: 7.8,
    color: C.muted,
    margin: 0,
    align: "center",
    fit: "shrink",
  });
}

function arrow(slide, x1, y1, x2, y2, color = C.blue) {
  slide.addShape(pptx.ShapeType.line, {
    x: x1,
    y: y1,
    w: x2 - x1,
    h: y2 - y1,
    line: { color, width: 1.3, beginArrowType: "none", endArrowType: "triangle" },
  });
}

function slide1() {
  const s = pptx.addSlide();
  s.background = { color: "F9FBFF" };
  s.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: W, h: H, fill: { color: "F9FBFF" }, line: { color: "F9FBFF" } });
  s.addShape(pptx.ShapeType.rect, { x: 0, y: 0, w: 0.42, h: H, fill: { color: C.blue }, line: { color: C.blue } });
  s.addShape(pptx.ShapeType.rect, { x: 0.42, y: 0, w: 0.16, h: H, fill: { color: C.cyan }, line: { color: C.cyan } });
  s.addText("Vyhledávání vzorů a technické analýzy kryptoměn", {
    x: 1.0,
    y: 1.55,
    w: 8.9,
    h: 1.2,
    fontFace: "Aptos Display",
    fontSize: 34,
    bold: true,
    color: C.ink,
    margin: 0,
    fit: "shrink",
  });
  s.addText("Architektura systému pro validaci obchodních pravidel, AI analýzu textů a prezentaci výsledků", {
    x: 1.02,
    y: 3.0,
    w: 7.7,
    h: 0.42,
    fontSize: 15,
    color: C.muted,
    margin: 0,
    fit: "shrink",
  });
  pill(s, "Python strategie", 1.03, 4.05, 1.55, C.blue, C.softBlue);
  pill(s, "PHP backend", 2.78, 4.05, 1.42, C.green, C.softGreen);
  pill(s, "MySQL", 4.4, 4.05, 0.98, C.amber, C.softAmber);
  pill(s, "AI wrapper", 5.58, 4.05, 1.3, C.cyan, C.softCyan);
  s.addText("Software Architecture Document", {
    x: 1.04,
    y: 6.32,
    w: 4.2,
    h: 0.3,
    fontSize: 10,
    color: C.muted,
    margin: 0,
  });
  s.addText("2026", {
    x: 11.15,
    y: 6.25,
    w: 1.0,
    h: 0.34,
    fontSize: 14,
    bold: true,
    color: C.blue,
    margin: 0,
    align: "right",
  });
}

function slide2() {
  const s = pptx.addSlide();
  addBg(s);
  title(s, "Cíl projektu", "Co má systém ověřit a proč vzniká");
  s.addText("Validovat obchodní pravidla nad reálnými kryptoměnovými daty", {
    x: 0.9,
    y: 2.0,
    w: 7.6,
    h: 0.75,
    fontSize: 25,
    bold: true,
    color: C.ink,
    margin: 0,
    fit: "shrink",
  });
  bulletList(
    s,
    [
      "generování signálů BUY / SELL / HOLD",
      "kombinace technické analýzy a tržního sentimentu",
      "ověření potenciálního zisku nebo ztráty pomocí backtestingu",
      "doplnění rozhodování o AI analýzu externích textů",
    ],
    0.95,
    3.2,
    7.5,
    { fontSize: 14, gap: 0.52 }
  );
  s.addText("Výstupem není pouze obchodní bot, ale architektura propojující analytiku, backend, databázi a prezentační vrstvu.", {
    x: 9.0,
    y: 1.95,
    w: 2.8,
    h: 2.4,
    fontSize: 17,
    bold: true,
    color: C.blue,
    margin: 0,
    fit: "shrink",
  });
  s.addShape(pptx.ShapeType.line, { x: 8.55, y: 1.85, w: 0, h: 3.4, line: { color: C.line, width: 1.2 } });
  addFooter(s, 2);
}

function slide3() {
  const s = pptx.addSlide();
  addBg(s);
  title(s, "Rozsah řešení", "Dvě související části: analytická a webová");
  card(s, 0.82, 1.65, 5.55, 4.35, "Python trading část", "Načítá data z Binance a CoinMarketCap, počítá SMA/EMA, vyhodnocuje strategii a ukládá rozhodnutí a obchody.", C.blue, "FFFFFF");
  card(s, 6.95, 1.65, 5.55, 4.35, "PHP backend a webová část", "Zajišťuje endpointy pro AI analýzu článků, historii událostí, Fear and Greed index a data zobrazovaná na webu serious.broker.", C.green, "FFFFFF");
  pill(s, "Binance", 1.25, 5.38, 1.05, C.blue, C.softBlue);
  pill(s, "SMA / EMA", 2.48, 5.38, 1.15, C.blue, C.softBlue);
  pill(s, "Backtesting", 3.82, 5.38, 1.32, C.blue, C.softBlue);
  pill(s, "OpenRouter", 7.38, 5.38, 1.32, C.green, C.softGreen);
  pill(s, "Články", 8.9, 5.38, 0.98, C.green, C.softGreen);
  pill(s, "FGI", 10.08, 5.38, 0.72, C.green, C.softGreen);
  addFooter(s, 3);
}

function slide4() {
  const s = pptx.addSlide();
  addBg(s);
  title(s, "Klíčové případy užití", "Co uživatel nebo systém reálně spouští");
  const items = [
    ["Vyhodnocení strategie", "Aplikace načte ceny a sentiment, vypočítá indikátor a vrátí BUY / SELL / HOLD.", C.blue],
    ["Backtesting", "Historická data slouží k ověření úspěšnosti pravidel před praktickým použitím.", C.cyan],
    ["AI analýza textu", "Uživatel zadá text nebo URL článku, backend vrátí sentiment, skóre a vysvětlení.", C.green],
    ["Prezentace výsledků", "Web zobrazuje historii událostí, Fear and Greed index a uložené analýzy.", C.amber],
  ];
  items.forEach((it, i) => {
    const x = i % 2 === 0 ? 0.85 : 6.85;
    const y = i < 2 ? 1.65 : 4.0;
    card(s, x, y, 5.55, 1.55, it[0], it[1], it[2], "FFFFFF");
  });
  addFooter(s, 4);
}

function slide5() {
  const s = pptx.addSlide();
  addBg(s);
  title(s, "Logický pohled", "Hlavní tok dat a odpovědností v systému");
  const xs = [0.65, 2.65, 4.65, 6.65, 8.65, 10.65];
  const labels = [
    ["Externí zdroje", "Binance, CMC, články", C.blue],
    ["Datová vrstva", "REST API, konfigurace", C.cyan],
    ["Indikátory", "SMA / EMA", C.green],
    ["Strategie", "BUY / SELL / HOLD", C.amber],
    ["Uložení", "MySQL + logy", C.red],
    ["Prezentace", "Web + statistiky", C.blue],
  ];
  labels.forEach((l, i) => {
    step(s, l[0], l[1], xs[i], 2.9, 1.55, l[2]);
    if (i < labels.length - 1) arrow(s, xs[i] + 1.55, 3.37, xs[i + 1] - 0.12, 3.37, C.muted);
  });
  s.addText("Oddělení modulů umožňuje měnit indikátory, strategii nebo AI wrapper bez přepisování celé aplikace.", {
    x: 1.2,
    y: 5.25,
    w: 10.4,
    h: 0.5,
    fontSize: 16,
    bold: true,
    color: C.ink,
    align: "center",
    margin: 0,
    fit: "shrink",
  });
  addFooter(s, 5);
}

function slide6() {
  const s = pptx.addSlide();
  addBg(s);
  title(s, "Procesní pohled", "Jeden synchronní obchodní cyklus Python části");
  const steps = [
    ["1", "Spuštění", "CLI nebo plánovač"],
    ["2", "Načtení dat", "ceny + FGI"],
    ["3", "Výpočet", "SMA nebo EMA"],
    ["4", "Rozhodnutí", "BUY / SELL / HOLD"],
    ["5", "Exekuce", "limity + zůstatky"],
    ["6", "Záznam", "MySQL + logy"],
  ];
  steps.forEach((st, i) => {
    const x = 0.8 + i * 2.05;
    s.addShape(pptx.ShapeType.ellipse, { x, y: 2.0, w: 0.58, h: 0.58, fill: { color: C.blue }, line: { color: C.blue } });
    s.addText(st[0], { x: x + 0.18, y: 2.14, w: 0.22, h: 0.16, fontSize: 10, bold: true, color: "FFFFFF", margin: 0, align: "center" });
    s.addText(st[1], { x: x - 0.32, y: 2.83, w: 1.2, h: 0.25, fontSize: 11.5, bold: true, color: C.ink, margin: 0, align: "center", fit: "shrink" });
    s.addText(st[2], { x: x - 0.38, y: 3.22, w: 1.34, h: 0.24, fontSize: 8.2, color: C.muted, margin: 0, align: "center", fit: "shrink" });
    if (i < steps.length - 1) arrow(s, x + 0.65, 2.29, x + 1.66, 2.29, C.line);
  });
  s.addText("V režimu --once proběhne jeden cyklus. V nepřetržitém režimu se cyklus opakuje podle intervalu v konfiguraci.", {
    x: 1.15,
    y: 5.2,
    w: 10.8,
    h: 0.42,
    fontSize: 15,
    color: C.ink,
    bold: true,
    align: "center",
    margin: 0,
    fit: "shrink",
  });
  addFooter(s, 6);
}

function slide7() {
  const s = pptx.addSlide();
  addBg(s);
  title(s, "AI wrapper a webový backend", "Doplňková fundamentální analýza nad externími texty");
  const y = 2.45;
  const nodes = [
    ["Uživatel", "text nebo URL", C.blue],
    ["PHP endpoint", "internal/ai-wrapper", C.green],
    ["OpenRouter", "LLM odpověď JSON", C.cyan],
    ["MySQL", "ai_analysis_results", C.amber],
    ["Web", "zobrazení výsledku", C.blue],
  ];
  nodes.forEach((n, i) => {
    const x = 0.9 + i * 2.42;
    step(s, n[0], n[1], x, y, 1.6, n[2]);
    if (i < nodes.length - 1) arrow(s, x + 1.62, y + 0.47, x + 2.25, y + 0.47, C.muted);
  });
  bulletList(
    s,
    [
      "výstup: sentiment, skóre a krátké vysvětlení v češtině",
      "uložení výsledku umožňuje historii analýz a statistiky sentimentu",
      "AI část je oddělená od obchodní logiky Python strategie",
    ],
    1.35,
    4.75,
    9.8,
    { fontSize: 13, gap: 0.45, dotColor: C.green }
  );
  addFooter(s, 7);
}

function slide8() {
  const s = pptx.addSlide();
  addBg(s);
  title(s, "Pohled nasazení", "Jednoduché nasazení bez zbytečné kontejnerizace");
  card(s, 0.95, 1.65, 3.55, 3.8, "Python proces", "Spouštění strategií, výpočet indikátorů, práce s Binance API a ukládání rozhodnutí.", C.blue);
  card(s, 4.9, 1.65, 3.55, 3.8, "PHP backend", "HTTP endpointy pro web, AI wrapper, články, FGI a historické události.", C.green);
  card(s, 8.85, 1.65, 3.55, 3.8, "MySQL databáze", "Sdílená perzistence pro výsledky strategií, obchody, AI analýzy a webová data.", C.amber);
  arrow(s, 4.5, 3.5, 4.85, 3.5, C.muted);
  arrow(s, 8.45, 3.5, 8.8, 3.5, C.muted);
  s.addText("Citlivé údaje jsou mimo zdrojový kód v .env / systémových proměnných.", {
    x: 1.2,
    y: 6.0,
    w: 10.8,
    h: 0.35,
    fontSize: 14,
    bold: true,
    color: C.ink,
    align: "center",
    margin: 0,
  });
  addFooter(s, 8);
}

function slide9() {
  const s = pptx.addSlide();
  addBg(s);
  title(s, "Kvalita architektury", "Co návrh chrání a co umožňuje dál rozvíjet");
  card(s, 0.85, 1.55, 3.65, 4.5, "Spolehlivost", "Při chybě API nebo chybějících datech systém nepokračuje agresivně, ale vrací bezpečný stav HOLD.", C.blue, C.softBlue);
  card(s, 4.85, 1.55, 3.65, 4.5, "Rozšiřitelnost", "Nový indikátor nebo datový zdroj lze přidat jako samostatný modul bez zásahu do celé architektury.", C.green, C.softGreen);
  card(s, 8.85, 1.55, 3.65, 4.5, "Bezpečnost", "API klíče jsou mimo repozitář, obchodování lze ověřovat přes dry_run a testy mockují riziková volání.", C.amber, C.softAmber);
  addFooter(s, 9);
}

function slide10() {
  const s = pptx.addSlide();
  addBg(s);
  title(s, "Testování a CI", "Ověření analytické logiky i komunikace s externími službami");
  s.addText("PyTest + GitHub Actions", {
    x: 0.95,
    y: 1.65,
    w: 5.5,
    h: 0.42,
    fontSize: 24,
    bold: true,
    color: C.blue,
    margin: 0,
  });
  bulletList(
    s,
    [
      "jednotkové testy výpočtů a pomocných funkcí",
      "testy chování při chybě API nebo chybějící konfiguraci",
      "mockování obchodních příkazů, aby nevznikly reálné obchody",
      "automatické spuštění testů v CI po změnách v repozitáři",
    ],
    0.98,
    2.45,
    6.9,
    { fontSize: 13.2, gap: 0.5, dotColor: C.blue }
  );
  s.addShape(pptx.ShapeType.roundRect, { x: 8.65, y: 1.75, w: 2.85, h: 0.95, rectRadius: 0.08, fill: { color: C.ink }, line: { color: C.ink } });
  s.addText("30 / 30", { x: 9.08, y: 1.94, w: 2.0, h: 0.34, fontSize: 22, bold: true, color: "FFFFFF", align: "center", margin: 0 });
  s.addText("testů prošlo", { x: 9.05, y: 2.33, w: 2.05, h: 0.16, fontSize: 8.2, color: "D6DEE8", align: "center", margin: 0, fit: "shrink" });
  s.addShape(pptx.ShapeType.roundRect, { x: 8.65, y: 3.0, w: 1.32, h: 0.98, rectRadius: 0.08, fill: { color: C.red }, line: { color: C.red } });
  s.addText("9 %", { x: 8.9, y: 3.23, w: 0.82, h: 0.28, fontSize: 19, bold: true, color: "FFFFFF", align: "center", margin: 0 });
  s.addText("celkem", { x: 8.86, y: 3.56, w: 0.9, h: 0.14, fontSize: 7.2, color: "FFE4E4", align: "center", margin: 0, fit: "shrink" });
  s.addShape(pptx.ShapeType.roundRect, { x: 10.18, y: 3.0, w: 1.32, h: 0.98, rectRadius: 0.08, fill: { color: C.green }, line: { color: C.green } });
  s.addText("83 %", { x: 10.42, y: 3.23, w: 0.85, h: 0.28, fontSize: 19, bold: true, color: "FFFFFF", align: "center", margin: 0 });
  s.addText("testované moduly", { x: 10.28, y: 3.56, w: 1.12, h: 0.14, fontSize: 6.6, color: "EAF8EF", align: "center", margin: 0, fit: "shrink" });
  s.addText("Coverage měří vykonané řádky v nastaveném rozsahu. Nízké celkové číslo vzniká tím, že provozní moduly pro trading loop, databázi a exekuci zatím nejsou plně pokryté testy.", {
    x: 8.55,
    y: 4.35,
    w: 3.25,
    h: 0.95,
    fontSize: 9.2,
    color: C.muted,
    margin: 0,
    fit: "shrink",
  });
  s.addShape(pptx.ShapeType.line, { x: 8.1, y: 1.55, w: 0, h: 4.7, line: { color: C.line, width: 1.2 } });
  addFooter(s, 10);
}

function slide11() {
  const s = pptx.addSlide();
  addBg(s);
  title(s, "Shrnutí", "Hlavní architektonická myšlenka");
  s.addText("Systém odděluje obchodní rozhodování, podpůrnou AI analýzu a prezentaci výsledků.", {
    x: 0.92,
    y: 1.75,
    w: 10.7,
    h: 0.86,
    fontSize: 28,
    bold: true,
    color: C.ink,
    margin: 0,
    fit: "shrink",
  });
  bulletList(
    s,
    [
      "Python část řeší strategii, indikátory, exekuci a backtesting.",
      "PHP backend zpřístupňuje webová data, AI wrapper a analytické endpointy.",
      "MySQL vytváří společnou perzistentní vrstvu pro výsledky a historii.",
      "Návrh je jednoduchý, modulární a vhodný pro další rozšiřování.",
    ],
    1.05,
    3.42,
    9.6,
    { fontSize: 14.5, gap: 0.53, dotColor: C.green }
  );
  s.addText("Děkuji za pozornost", {
    x: 1.05,
    y: 6.15,
    w: 4.5,
    h: 0.35,
    fontSize: 16,
    bold: true,
    color: C.blue,
    margin: 0,
  });
  addFooter(s, 11);
}

[
  slide1,
  slide2,
  slide3,
  slide4,
  slide5,
  slide6,
  slide7,
  slide8,
  slide9,
  slide10,
  slide11,
].forEach((fn) => fn());

const outFile =
  process.env.PPTX_OUT ||
  "docs/presentation/architektura_kryptomen_prezentace.pptx";
pptx.writeFile({ fileName: outFile });

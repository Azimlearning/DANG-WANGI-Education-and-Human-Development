// The Kit's own fixed words, in English and Bahasa Melayu (W12, D-62). A page chooses its language once, in `environment({ lang })`, before any part is made;
// nothing translates at run time. Words that come from a Plan (titles, sentences, labels) are not here: a Malay page is built from a Malay Plan, so every
// check that holds for the English page holds for it. These strings are DRAFTS written by the build assistant and are not shown to students until a fluent
// reviewer has approved them (the review sheet lists them with the Plan strings); see refdocs/plans/2026-10-27-w12-bahasa-melayu.md.
//
// A key whose English is a function takes arguments (a count, a name), so word order can differ between the languages.

export type Lang = "en" | "ms";

interface Entry<A extends unknown[] = []> {
  en: string | ((...a: A) => string);
  ms: string | ((...a: A) => string);
}

const stage = <A extends unknown[]>(e: Entry<A>): Entry<A> => e;

export const WORDS = {
  tryThis: stage({ en: "Try this:", ms: "Cuba ini:" }),
  keyIdea: stage({ en: "Key idea:", ms: "Idea utama:" }),
  stage: stage({ en: "Stage", ms: "Pentas" }),
  controls: stage({ en: "Controls", ms: "Kawalan" }),
  readouts: stage({ en: "Readouts", ms: "Bacaan" }),
  steps: stage({ en: "Steps", ms: "Langkah" }),
  record: stage({ en: "Record", ms: "Rekod" }),
  clear: stage({ en: "Clear", ms: "Kosongkan" }),
  rowRecorded: stage({ en: "Row recorded", ms: "Baris direkodkan" }),
  tableCleared: stage({ en: "Table cleared", ms: "Jadual dikosongkan" }),
  showHint: stage({ en: "Show a hint", ms: "Tunjukkan petunjuk" }),
  checkTitle: stage({ en: "Check your understanding", ms: "Semak kefahaman anda" }),
  options: stage({ en: "Options", ms: "Pilihan" }),
  correct: stage({ en: "Correct.", ms: "Betul." }),
  notQuite: stage({ en: "Not quite.", ms: "Belum tepat." }),
  predictTitle: stage({ en: "Make a prediction", ms: "Buat ramalan" }),
  yourPrediction: stage({ en: "Your prediction", ms: "Ramalan anda" }),
  reset: stage({ en: "Reset", ms: "Set semula" }),
  workedTitle: stage({ en: "Worked solution", ms: "Penyelesaian berlangkah" }),
  showWorked: stage({ en: "Show the worked solution", ms: "Tunjukkan penyelesaian berlangkah" }),
  experimentTitle: stage({ en: "Experiment", ms: "Eksperimen" }),
  aim: stage({ en: "Aim", ms: "Tujuan" }),
  hypothesis: stage({ en: "Hypothesis", ms: "Hipotesis" }),
  changed: stage({ en: "Changed (manipulated variable)", ms: "Diubah (pemboleh ubah dimanipulasikan)" }),
  measured: stage({ en: "Measured (responding variable)", ms: "Diukur (pemboleh ubah bergerak balas)" }),
  kept: stage({ en: "Kept the same (fixed variables)", ms: "Dimalarkan (pemboleh ubah dimalarkan)" }),
  apparatus: stage({ en: "Apparatus", ms: "Radas" }),
  graphOf: stage<[string, string, string]>({ en: (y, x, title) => `Graph of ${y} against ${x}. ${title}`, ms: (y, x, title) => `Graf ${y} melawan ${x}. ${title}` }),
  against: stage<[string, string]>({ en: (y, x) => `${y} against ${x}`, ms: (y, x) => `${y} melawan ${x}` }),

  // The mass bench.
  massCount: stage<[number]>({
    en: (n) => ["no masses", "one mass", "two masses", "three masses", "four masses", "five masses", "six masses", "seven masses", "eight masses"][n] ?? `${n} masses`,
    ms: (n) => ["tiada jisim", "satu jisim", "dua jisim", "tiga jisim", "empat jisim", "lima jisim", "enam jisim", "tujuh jisim", "lapan jisim"][n] ?? `${n} jisim`,
  }),
  massesToHang: stage<[string]>({ en: (label) => `${label}: masses to hang`, ms: (label) => `${label}: jisim untuk digantung` }),
  tray: stage({ en: "Tray", ms: "Dulang" }),
  hanger: stage({ en: "Hanger", ms: "Penggantung" }),
  trayLabel: stage({ en: "Masses in the tray", ms: "Jisim di dalam dulang" }),
  hangerHolding: stage<[string]>({ en: (w) => `Hanger, holding ${w}`, ms: (w) => `Penggantung, memegang ${w}` }),
  massName: stage<[string, boolean]>({
    en: (letter, onHanger) => `Mass ${letter}, ${onHanger ? "on the hanger" : "in the tray"}. Press Enter to move it.`,
    ms: (letter, onHanger) => `Jisim ${letter}, ${onHanger ? "pada penggantung" : "di dalam dulang"}. Tekan Enter untuk menggerakkannya.`,
  }),

  // The burette's stopcock and the eye.
  stopcock: stage({ en: "Stopcock", ms: "Pili" }),
  stopcockName: stage({ en: "Stopcock. Hold to run the liquid, or press to let out one measure.", ms: "Pili. Tahan untuk mengalirkan cecair, atau tekan untuk melepaskan satu sukatan." }),
  stopcockOpen: stage({ en: "Stopcock open: the liquid is running.", ms: "Pili terbuka: cecair sedang mengalir." }),
  stopcockLimit: stage({ en: "Stopcock closed: the burette is at its limit.", ms: "Pili tertutup: buret telah sampai had." }),
  stopcockClosed: stage({ en: "Stopcock closed.", ms: "Pili tertutup." }),
  eye: stage({ en: "Eye", ms: "Mata" }),
  eyeName: stage({
    en: "Your eye. Drag up or down the burette, or press the up and down arrow keys, to read the meniscus.",
    ms: "Mata anda. Seret ke atas atau ke bawah buret, atau tekan kekunci anak panah atas dan bawah, untuk membaca meniskus.",
  }),

  // Scenes.
  springHanging: stage<[string]>({ en: (w) => `A spring hanging from a bracket, ${w}.`, ms: (w) => `Sebuah spring tergantung pada pendakap, ${w}.` }),
  stretch0: stage({ en: "not stretched", ms: "tidak diregangkan" }),
  stretch1: stage({ en: "stretched a little", ms: "diregangkan sedikit" }),
  stretch2: stage({ en: "stretched a fair amount", ms: "diregangkan agak banyak" }),
  stretch3: stage({ en: "stretched a lot", ms: "diregangkan banyak" }),

  buretteFull: stage({ en: "full", ms: "penuh" }),
  buretteNearlyFull: stage({ en: "nearly full", ms: "hampir penuh" }),
  buretteHalf: stage({ en: "about half empty", ms: "kira-kira separuh kosong" }),
  buretteNearlyEmpty: stage({ en: "nearly empty", ms: "hampir kosong" }),
  eyeLevel: stage({ en: "Your eye is level with the meniscus, so this is a fair reading.", ms: "Mata anda sejajar dengan meniskus, jadi bacaan ini adil." }),
  eyeAbove: stage({ en: "Your eye is above the meniscus. Bring it level with the meniscus before you read.", ms: "Mata anda berada di atas meniskus. Sejajarkan dengan meniskus sebelum anda membaca." }),
  eyeBelow: stage({ en: "Your eye is below the meniscus. Bring it level with the meniscus before you read.", ms: "Mata anda berada di bawah meniskus. Sejajarkan dengan meniskus sebelum anda membaca." }),
  buretteScene: stage<[string, boolean]>({
    en: (w, pink) => `A burette above a flask: the burette is ${w}, and the liquid in the flask ${pink ? "has turned pink" : "is still colourless"}.`,
    ms: (w, pink) => `Sebuah buret di atas kelalang: buret itu ${w}, dan cecair di dalam kelalang ${pink ? "telah bertukar merah jambu" : "masih tidak berwarna"}.`,
  }),

  bubblesFew: stage({ en: "a few bubbles", ms: "beberapa gelembung" }),
  bubblesSteady: stage({ en: "steady bubbling", ms: "gelembung yang stabil" }),
  bubblesPlenty: stage({ en: "plenty of bubbles", ms: "banyak gelembung" }),
  fermentActive: stage<[string]>({
    en: (b) => `Tube A: gas bubbles through the delivery tube (${b}), the limewater has turned cloudy, the tube is warmer and it smells of ethanol. Tube B, the control: the limewater is clear and nothing has changed.`,
    ms: (b) => `Tabung A: gas menggelegak melalui tiub penghantar (${b}), air kapur telah menjadi keruh, tabung itu lebih panas dan berbau etanol. Tabung B, kawalan: air kapur kekal jernih dan tiada apa-apa yang berubah.`,
  }),
  fermentIdle: stage({ en: "Nothing has happened yet: both limewaters are clear and both tubes are at the same temperature.", ms: "Belum ada apa-apa yang berlaku: kedua-dua air kapur jernih dan kedua-dua tabung berada pada suhu yang sama." }),
  fermentScene: stage<[string]>({
    en: (obs) => `Two boiling tubes under paraffin oil, A with yeast and B without, each with a delivery tube into limewater. ${obs}`,
    ms: (obs) => `Dua tabung didih di bawah minyak parafin, A dengan yis dan B tanpa yis, masing-masing dengan tiub penghantar ke dalam air kapur. ${obs}`,
  }),

  earth: stage({ en: "Earth", ms: "Bumi" }),
  launch: stage({ en: "Launch", ms: "Lancarkan" }),

  planet1: stage({ en: "Mercury", ms: "Utarid" }),
  planet2: stage({ en: "Venus", ms: "Zuhrah" }),
  planet3: stage({ en: "Earth", ms: "Bumi" }),
  planet4: stage({ en: "Mars", ms: "Marikh" }),
  planet5: stage({ en: "Jupiter", ms: "Musytari" }),
  planet6: stage({ en: "Saturn", ms: "Zuhal" }),
  planet7: stage({ en: "Uranus", ms: "Uranus" }),
  planet8: stage({ en: "Neptune", ms: "Neptun" }),
  ordinal1: stage({ en: "first", ms: "pertama" }),
  ordinal2: stage({ en: "second", ms: "kedua" }),
  ordinal3: stage({ en: "third", ms: "ketiga" }),
  ordinal4: stage({ en: "fourth", ms: "keempat" }),
  ordinal5: stage({ en: "fifth", ms: "kelima" }),
  ordinal6: stage({ en: "sixth", ms: "keenam" }),
  ordinal7: stage({ en: "seventh", ms: "ketujuh" }),
  ordinal8: stage({ en: "eighth", ms: "kelapan" }),
  planetsHint: stage({ en: "Drag the test mass to another planet, or tap a planet.", ms: "Seret jisim ujian ke planet lain, atau ketik sebuah planet." }),
  planetsScene: stage<[string, string]>({
    en: (name, ordinal) => `The eight planets in order from the Sun, drawn bigger or smaller by size but not to scale. The test mass on its spring balance is on ${name}, the ${ordinal} planet from the Sun.`,
    ms: (name, ordinal) => `Lapan planet mengikut susunan dari Matahari, dilukis lebih besar atau lebih kecil mengikut saiz tetapi tidak mengikut skala. Jisim ujian pada neraca spring berada di ${name}, planet ${ordinal} dari Matahari.`,
  }),
  orbitFalls: stage({ en: "The cannonball is too slow: it curves down and lands on Earth.", ms: "Bola meriam terlalu perlahan: ia melengkung ke bawah dan mendarat di Bumi." }),
  orbitCircle: stage({ en: "The cannonball goes round Earth in a circle: it keeps falling but keeps missing the ground.", ms: "Bola meriam mengelilingi Bumi dalam bentuk bulatan: ia terus jatuh tetapi terus terlepas daripada tanah." }),
  orbitOval: stage({ en: "The cannonball goes round Earth in an oval, moving away from Earth and then back towards it.", ms: "Bola meriam mengelilingi Bumi dalam bentuk bujur, bergerak menjauhi Bumi dan kemudian kembali ke arahnya." }),
  orbitEscapes: stage({ en: "The cannonball is fast enough to leave Earth and never comes back.", ms: "Bola meriam cukup laju untuk meninggalkan Bumi dan tidak kembali lagi." }),
  orbitSketch: stage({ en: "The path is worked out for a cannon on a very tall mountain, far taller than a real one, and the picture is not to scale.", ms: "Lintasan dikira untuk meriam di atas gunung yang sangat tinggi, jauh lebih tinggi daripada gunung sebenar, dan gambar ini tidak mengikut skala." }),
  orbitScene: stage<[string, string]>({
    en: (outcome, sketch) => `A cannon on a tall mountain fires sideways over Earth. ${outcome} ${sketch}`,
    ms: (outcome, sketch) => `Sebuah meriam di atas gunung yang tinggi menembak ke sisi di atas Bumi. ${outcome} ${sketch}`,
  }),

  refrAir: stage({ en: "Air", ms: "Udara" }),
  refrMedium: stage({ en: "Denser medium", ms: "Medium lebih tumpat" }),
  refrNormal: stage({ en: "Normal", ms: "Garis normal" }),
  refrStraight: stage({ en: "The ray travels along the normal and goes straight on without bending.", ms: "Sinar bergerak di sepanjang garis normal dan terus lurus tanpa membengkok." }),
  refrSame: stage({ en: "The ray does not bend, because light travels at the same speed in both media.", ms: "Sinar tidak membengkok kerana cahaya bergerak pada laju yang sama dalam kedua-dua medium." }),
  refrBends: stage({
    en: "The ray bends towards the normal as it enters the denser medium, so the angle of refraction is smaller than the angle of incidence.",
    ms: "Sinar membengkok ke arah garis normal apabila memasuki medium yang lebih tumpat, jadi sudut biasan lebih kecil daripada sudut tuju.",
  }),
  refrScene: stage<[string]>({ en: (w) => `A ray of light passes from air into a denser medium. ${w}`, ms: (w) => `Sinar cahaya bergerak dari udara ke dalam medium yang lebih tumpat. ${w}` }),

  pressureSurfaceLabel: stage({ en: "Surface", ms: "Permukaan" }),
  pressureSurface: stage({ en: "The probe is at the surface, with no liquid above it pressing down.", ms: "Prob berada di permukaan, tanpa cecair di atasnya yang menekan." }),
  pressureLow: stage({ en: "The probe is a little way down: the liquid presses on it gently from every side.", ms: "Prob berada sedikit ke bawah: cecair menekannya dengan perlahan dari semua arah." }),
  pressureMid: stage({ en: "The probe is a fair way down: more liquid above means the liquid presses on it harder.", ms: "Prob berada agak dalam: lebih banyak cecair di atas bermakna cecair menekannya dengan lebih kuat." }),
  pressureHigh: stage({ en: "The probe is deep down: the liquid above presses on it hardest, from every side.", ms: "Prob berada jauh di bawah: cecair di atas menekannya paling kuat, dari semua arah." }),
  pressureScene: stage<[string]>({ en: (w) => `A tank of liquid with a small probe in it. ${w}`, ms: (w) => `Sebuah tangki berisi cecair dengan sebuah prob kecil di dalamnya. ${w}` }),

  appBench: stage({ en: "Apparatus on the bench", ms: "Radas di atas meja" }),
  appSentence: stage<[string, string, string]>({ en: (part, label, rest) => `${part}, ${label}: ${rest}.`, ms: (part, label, rest) => `${part} (${label}): ${rest}.` }),
  app_beaker: stage({ en: "Beaker", ms: "Bikar" }),
  app_flask: stage({ en: "Conical flask", ms: "Kelalang kon" }),
  app_test_tube: stage({ en: "Test tube", ms: "Tabung uji" }),
  app_cylinder: stage({ en: "Measuring cylinder", ms: "Silinder penyukat" }),
  app_solution: stage({ en: "Solution", ms: "Larutan" }),
  app_indicator: stage({ en: "Indicator", ms: "Penunjuk" }),
  app_syringe: stage({ en: "Gas syringe", ms: "Picagari gas" }),
  app_burner: stage({ en: "Bunsen burner", ms: "Penunu Bunsen" }),
  app_thermometer: stage({ en: "Thermometer", ms: "Termometer" }),
  app_balance: stage({ en: "Balance", ms: "Penimbang" }),
  app_gauge: stage({ en: "Gauge", ms: "Tolok" }),
  app_weights: stage({ en: "Slotted masses", ms: "Pemberat berslot" }),
  app_spring: stage({ en: "Coiled spring", ms: "Spring lingkaran" }),
  app_trolley: stage({ en: "Trolley", ms: "Troli" }),
  app_ramp: stage({ en: "Slope", ms: "Satah condong" }),
  app_pendulum: stage({ en: "Pendulum", ms: "Bandul" }),
  app_bulb: stage({ en: "Bulb", ms: "Mentol" }),
  app_circuit: stage({ en: "Circuit", ms: "Litar" }),
  app_coils: stage({ en: "Transformer coils", ms: "Gegelung transformer" }),
  app_wave: stage({ en: "Wave", ms: "Gelombang" }),
  app_orbit: stage({ en: "Orbit", ms: "Laluan orbit" }),
  app_particles: stage({ en: "Gas particles", ms: "Zarah gas" }),
  app_nuclei: stage({ en: "Nuclei", ms: "Nukleus-nukleus" }),
  app_leaf: stage({ en: "Water plant", ms: "Tumbuhan akuatik" }),
  app_cell: stage({ en: "Cell", ms: "Sel hidup" }),
  app_field: stage({ en: "Field", ms: "Padang" }),
  appch_level: stage({ en: "level", ms: "aras" }),
  appch_bubbles: stage({ en: "bubbling", ms: "gelembung" }),
  appch_concentration: stage({ en: "concentration", ms: "kepekatan" }),
  appch_ph: stage({ en: "pH", ms: "nilai pH" }),
  appch_volume: stage({ en: "volume", ms: "isi padu" }),
  appch_heat: stage({ en: "flame", ms: "nyalaan" }),
  appch_temperature: stage({ en: "temperature", ms: "suhu" }),
  appch_mass: stage({ en: "mass", ms: "jisim" }),
  appch_value: stage({ en: "reading", ms: "bacaan" }),
  appch_load: stage({ en: "load", ms: "beban" }),
  appch_extension: stage({ en: "extension", ms: "pemanjangan" }),
  appch_position: stage({ en: "position", ms: "kedudukan" }),
  appch_speed: stage({ en: "speed", ms: "laju" }),
  appch_angle: stage({ en: "slope", ms: "kecerunan" }),
  appch_length: stage({ en: "length", ms: "panjang" }),
  appch_brightness: stage({ en: "brightness", ms: "kecerahan" }),
  appch_current: stage({ en: "current", ms: "arus" }),
  appch_primary: stage({ en: "primary turns", ms: "lilitan primer" }),
  appch_secondary: stage({ en: "secondary turns", ms: "lilitan sekunder" }),
  appch_amplitude: stage({ en: "amplitude", ms: "amplitud" }),
  appch_wavelength: stage({ en: "wavelength", ms: "panjang gelombang" }),
  appch_frequency: stage({ en: "frequency", ms: "frekuensi" }),
  appch_radius: stage({ en: "orbit size", ms: "saiz orbit" }),
  appch_remaining: stage({ en: "left undecayed", ms: "belum mereput" }),
  appch_light: stage({ en: "light", ms: "cahaya" }),
  appch_rate: stage({ en: "rate", ms: "kadar" }),
  appch_size: stage({ en: "size", ms: "saiz" }),
  appch_density: stage({ en: "density", ms: "ketumpatan" }),
  applv0: stage({ en: "none", ms: "tiada" }),
  applv1: stage({ en: "low", ms: "rendah" }),
  applv2: stage({ en: "medium", ms: "sederhana" }),
  applv3: stage({ en: "high", ms: "tinggi" }),
  applv4: stage({ en: "very high", ms: "sangat tinggi" }),
  appph0: stage({ en: "strongly acidic", ms: "berasid kuat" }),
  appph1: stage({ en: "weakly acidic", ms: "berasid lemah" }),
  appph2: stage({ en: "neutral", ms: "bersifat neutral" }),
  appph3: stage({ en: "weakly alkaline", ms: "beralkali lemah" }),
  appph4: stage({ en: "strongly alkaline", ms: "beralkali kuat" }),
  // The hands-on bench (W17): grips on the drawing and things dropped into a part.
  appGrab: stage({ en: "Drag the round handles on the apparatus, or use the sliders.", ms: "Seret pemegang bulat pada radas, atau gunakan peluncur." }),
  dropCount: stage<[number]>({
    en: (n) => ["nothing added", "one added", "two added", "three added", "four added", "five added", "six added", "seven added", "eight added"][n] ?? "many added",
    ms: (n) => ["tiada yang ditambah", "satu ditambah", "dua ditambah", "tiga ditambah", "empat ditambah", "lima ditambah", "enam ditambah", "tujuh ditambah", "lapan ditambah"][n] ?? "banyak ditambah",
  }),
  dropZone: stage<[string, string]>({ en: (label, count) => `${label}, ${count}. Drop items here.`, ms: (label, count) => `${label}, ${count}. Letakkan item di sini.` }),
  dropTray: stage<[string]>({ en: (item) => `${item}: drag onto the apparatus`, ms: (item) => `${item}: seret ke atas radas` }),
  dropName: stage<[string, string, boolean]>({
    en: (item, letter, added) => `${item} ${letter}, ${added ? "added" : "in the tray"}. Press Enter to move it.`,
    ms: (item, letter, added) => `${item} ${letter}, ${added ? "sudah ditambah" : "di dalam dulang"}. Tekan Enter untuk menggerakkannya.`,
  }),
} as const;

export type WordKey = keyof typeof WORDS;

let current: Lang = "en";

/** The language of the page being built. `environment()` sets it; the default is English. */
export function setLanguage(lang: Lang): void {
  if (lang !== "en" && lang !== "ms") throw new RangeError(`environment: lang must be "en" or "ms"`);
  current = lang;
}

export function language(): Lang {
  return current;
}

/** A fixed word that takes no arguments, by a key made at run time (a part's or a channel's name). Throws for a key that is missing or that takes arguments. */
export function ktWord(key: string): string {
  const entry = (WORDS as Record<string, Entry<unknown[]> | undefined>)[key];
  const value = entry?.[current];
  if (typeof value !== "string") throw new RangeError(`no fixed word '${key}'`);
  return value;
}

/** The Kit's fixed word for `key` in the page's language. */
export function kt<K extends WordKey>(key: K, ...args: (typeof WORDS)[K] extends Entry<infer A> ? A : never): string {
  const entry = WORDS[key] as Entry<unknown[]>;
  const value = entry[current];
  return typeof value === "function" ? value(...args) : value;
}

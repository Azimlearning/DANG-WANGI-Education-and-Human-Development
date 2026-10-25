/** How a citation reads to a student. The stored citation names the corpus document by its file id (for example `textbook-physics-physics-f5-removed`)
 * and a PDF page; the student should see a book and a page. The title is derived from the id's own words, so nothing here is textbook content, and
 * an id that does not follow the pattern is shown as it is, never guessed at. The printed page number is not recorded, so the page is called a PDF page.
 * (api/evidence/titles.py does the same for the offline export; the two are tested against the same ids.) */

const SUBJECTS: Record<string, string> = { physics: "Physics", chemistry: "Chemistry", biology: "Biology" };

export function documentTitle(source: string): string {
  const m = /^textbook-(physics|chemistry|biology)(?:-.*?)?-(?:f|form-?)([45])(?:-|$)/.exec(source);
  const subject = m?.[1] ? SUBJECTS[m[1]] : undefined;
  return m && subject ? `KSSM ${subject} Form ${m[2]} textbook` : source;
}

export function citationText(c: { source: string; page: number | null; verified: boolean }): string {
  const where = c.page !== null ? `, PDF page ${c.page}` : "";
  return `${documentTitle(c.source)}${where}${c.verified ? "" : " (not verified)"}`;
}

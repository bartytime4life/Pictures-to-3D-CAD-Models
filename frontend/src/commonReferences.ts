/** Nominal reference sizes, not measured tolerances or automatic object detection.
 * Source checked 2026-11-16. Keep SI dimensions as the single conversion basis.
 */
const MINT_SPECIFICATIONS =
  'https://www.usmint.gov/learn/coins-and-medals/circulating-coins/coin-specifications';

export const COMMON_REFERENCES = [
  { id: 'us-quarter', label: 'U.S. quarter', lengthMm: 24.26 },
  { id: 'us-penny', label: 'U.S. penny', lengthMm: 19.05 },
  { id: 'us-nickel', label: 'U.S. nickel', lengthMm: 21.21 },
  { id: 'us-dime', label: 'U.S. dime', lengthMm: 17.91 },
].map((item) => ({
  ...item,
  feature: 'diameter',
  instruction: 'Mark opposite edges through the center of the visible coin.',
  sourceTitle: 'U.S. Mint coin specifications',
  sourceUrl: MINT_SPECIFICATIONS,
}));

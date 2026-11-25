/** Symbole FaceIN : deux portes hexagonales complémentaires (logo officiel). */
export function BrandMark({ inverted = false }: { inverted?: boolean }) {
  return (
    <svg className="brand-mark" viewBox="56 30 281 317" aria-hidden="true" focusable="false">
      <path d="M190 37L256 73L125 150V224L192 264L128 301L63 264V109Z" fill={inverted ? "#FFFFFF" : "#0D1B31"} />
      <path d="M266 80L330 116V267L203 340L139 303L270 228V152L205 115Z" fill="#3369F6" />
    </svg>
  );
}

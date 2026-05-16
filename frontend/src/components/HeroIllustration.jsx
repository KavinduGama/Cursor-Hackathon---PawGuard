/**
 * Hero artwork for the landing page — golden retriever puppy + tabby kitten
 * surrounded by soft green foliage. Rendered as an <img> so the illustration
 * matches the hi-fi mockup faithfully.
 */
export default function HeroIllustration({ className = '' }) {
  return (
    <img
      className={className}
      src="/hero-pets.jpg"
      alt=""
      aria-hidden
      draggable={false}
    />
  );
}

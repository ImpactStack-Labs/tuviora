import { Link } from 'react-router-dom'

export default function TuvioraLogo({
  className = '',
  imageClassName = 'h-12 w-auto max-w-[185px]',
  dark = false,
}) {
  return (
    <Link
      to="/"
      aria-label="Tuviora home"
      className={`inline-flex shrink-0 items-center rounded-lg ${
        ''
      } ${className}`}
    >
      <img
        src={dark ? "/images/tuviora-logo-white.png" : "/images/tuviora-logo.png"}
        alt="Tuviora"
        className={`${imageClassName} object-contain`}
      />
    </Link>
  )
}

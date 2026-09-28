import Image from 'next/image';

export function BrandMark({ size = 36, className = '', alt = '' }: { size?: number; className?: string; alt?: string }) {
  return (
    <Image
      src="/vaultpulse-mark.svg"
      alt={alt}
      width={size}
      height={size}
      className={className}
    />
  );
}

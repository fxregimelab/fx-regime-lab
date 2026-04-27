export function LogoMark({ size = 24 }: { size?: number }) {
  // Since we don't have the logo in the public folder yet, we will just use a colored dot or placeholder 
  // Wait, the user has "logo without bg.png" in the root directory. 
  // I should use an HTML div as a placeholder or we can copy it later.
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        background: 'linear-gradient(135deg, #4BA3E3, #F5923A)',
        display: 'block',
        flexShrink: 0,
      }}
    />
  );
}

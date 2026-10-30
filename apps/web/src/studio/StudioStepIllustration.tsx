/** Decorative storybook scenes; each scene is described by the adjacent step. */
export function StudioStepIllustration({ step }: { step: number }) {
  const ink = "#294463";
  const paper = "#fff7e5";
  const teal = "#7eb6a5";
  const gold = "#efb65c";

  return (
    <svg className="studio-step-art" viewBox="0 0 280 170" fill="none" aria-hidden="true" focusable="false">
      <ellipse cx="140" cy="148" rx="94" ry="9" fill={ink} opacity=".12" />
      <ellipse cx="140" cy="87" rx="108" ry="68" fill={teal} opacity=".12" />
      <g stroke={ink} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        {step === 0 ? (
          <>
            <g transform="rotate(-7 124 85)">
              <rect x="67" y="27" width="117" height="124" rx="12" fill={paper} />
              <rect x="99" y="18" width="53" height="19" rx="7" fill={teal} />
              <path d="M113 18a12 12 0 0 1 24 0" />
              <circle cx="96" cy="62" r="13" fill="#ecd5ba" stroke="none" />
              <path d="M81 83c2-17 28-17 30 0" fill={teal} />
              <path d="M122 61h39M122 73h27M85 104h73M85 118h55M85 132h36" opacity=".55" />
            </g>
            <g transform="rotate(9 196 106)">
              <rect x="164" y="71" width="68" height="66" rx="8" fill="white" />
              <rect x="172" y="79" width="52" height="43" rx="4" fill="#dcebe3" stroke="none" />
              <circle cx="210" cy="90" r="6" fill={gold} stroke="none" />
              <path d="m173 115 14-16 12 12 10-7 14 17h-50Z" fill={teal} stroke="none" />
            </g>
            <g transform="rotate(29 200 49)">
              <path d="M193 27h14v49l-7 13-7-13Z" fill={gold} />
              <path d="M193 36h14M193 76h14M200 82v7" />
              <path d="M193 27v-6a7 7 0 0 1 14 0v6" fill="#d69682" />
            </g>
          </>
        ) : step === 1 ? (
          <>
            <path d="M42 69 140 81l98-12v72c-40-5-65 1-98 14-34-13-59-19-98-14Z" fill={teal} />
            <path d="M49 51c34-4 63 5 91 20 28-15 57-24 91-20v81c-35-3-63 5-91 18-28-13-56-21-91-18Z" fill={paper} />
            <path d="M140 71v79" opacity=".5" />
            <path d="M61 116c24-16 43-5 66 7v-38c-23-16-43-22-66-20Z" fill="#dcebe3" stroke="none" />
            <circle cx="110" cy="82" r="8" fill={gold} stroke="none" />
            <path d="m62 112 18-18 16 14 12-9 19 20v8c-25-11-42-16-65-8Z" fill={teal} stroke="none" />
            <path d="M155 91c22-12 39-16 61-16M155 105c22-12 39-16 61-16M155 119c17-9 30-13 43-14" opacity=".4" />
            <path d="m187 52 24-27" stroke={gold} strokeWidth="7" />
            <path d="m217 13 3 9 9 3-9 3-3 9-3-9-9-3 9-3Z" fill={gold} stroke="none" />
            <path d="m91 30 2 6 6 2-6 2-2 6-2-6-6-2 6-2Z" fill={gold} stroke="none" />
            <path d="M155 36v10M150 41h10" stroke={teal} />
          </>
        ) : (
          <>
            <g transform="rotate(-8 134 86)">
              <rect x="81" y="24" width="107" height="125" rx="9" fill={teal} />
              <path d="M92 25v123" opacity=".45" />
              <rect x="102" y="38" width="73" height="96" rx="6" fill={paper} stroke="none" />
              <path d="m149 24 0 27 8-6 8 6V24" fill={gold} stroke="none" />
              <circle cx="137" cy="77" r="12" fill="#ecd5ba" stroke="none" />
              <path d="M118 107c0-22 38-22 38 0" fill={teal} stroke="none" />
              <path d="M119 118h34" opacity=".5" />
            </g>
            <path d="M70 148c-9-7-17-18-22-31-3-8 4-13 9-6l14 17 18 7M72 151l22-13" fill="#ecd5ba" />
            <path d="M197 148c10-8 18-19 23-32 3-8-4-13-9-6l-14 17-17 8M197 151l-22-13" fill="#ecd5ba" />
            <circle cx="204" cy="55" r="25" fill="#518c77" stroke={paper} strokeWidth="4" />
            <path d="m193 55 7 7 14-15" stroke={paper} strokeWidth="4" />
          </>
        )}
      </g>
      <g fill={gold}>
        <path d="m45 42 2 7 7 2-7 2-2 7-2-7-7-2 7-2Z" />
        <path d="m241 105 2 6 6 2-6 2-2 6-2-6-6-2 6-2Z" />
        <circle cx="234" cy="43" r="2.5" />
      </g>
    </svg>
  );
}

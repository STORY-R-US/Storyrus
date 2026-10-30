import type { ReactNode } from "react";
import { StudioStepIllustration } from "./StudioStepIllustration";

export function StudioStageHeading({ title, illustration, id, level = "h3", children }: {
  title: ReactNode; illustration: number; id?: string; level?: "h1" | "h3"; children?: ReactNode;
}) {
  const Heading = level;
  return (
    <div className="studio-stage-heading">
      <div className="studio-stage-copy">
        <Heading id={id}>{title}</Heading>
        {children}
      </div>
      <StudioStepIllustration step={illustration} />
    </div>
  );
}

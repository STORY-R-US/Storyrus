import type { Job } from "../types";
import type { StudioCopy } from "./i18n";

export function uncertainGeneration(message?: string | null, job?: Job | null): boolean {
  return /GENERATION_OUTCOME_UNKNOWN/i.test(message || "") ||
    job?.result?.last_provider_error?.outcome_unknown === true;
}

export function generationError(t: StudioCopy, message?: string | null, job?: Job | null) {
  if (uncertainGeneration(message, job)) {
    const requestId = job?.result?.last_provider_error?.client_request_id ||
      job?.result?.last_provider_error?.request_id;
    return `${t.previewGenerationOutcomeUnknown}${requestId ? ` ${t.previewRequestId}: ${requestId}` : ""}`;
  }
  if (/BOOK_LAYOUT_UNSAFE/.test(message || "")) return t.previewNoSafeTextArea;
  if (/BOOK_TEXT_INVALID/.test(message || "")) return t.previewBookTextInvalid;
  if (/BOOK_REVIEW_INVALID/.test(message || "")) return t.previewBookReviewInvalid;
  if (/BOOK_ART_(?:UNAVAILABLE|INVALID)|Arte original armazenada|Arte editorial armazenada|Arquivo da capa alterado/.test(message || "")) return t.previewBookArtUnavailable;
  if (/BOOK_ART_REJECTED|Capa ou ilustração reprovada/.test(message || "")) return t.previewBookArtRejected;
  if (/INPUT_SAFETY_BLOCKED/i.test(message || "")) return t.previewInputSafetyBlocked;
  if (/moderation_block|content_policy_violation/i.test(message || "")) return t.previewProviderSafetyBlocked;
  if (/INPUT_SAFETY_CHECK_INVALID_IMAGE/i.test(message || "")) return t.previewInvalidPhoto;
  if (/INPUT_SAFETY_CHECK_(?:UNAVAILABLE|INVALID)/i.test(message || "")) return t.previewSafetyCheckUnavailable;
  if (/OpenAI \d{3}:|image_generation_user_error/i.test(message || "")) return t.previewProviderFailed;
  return message;
}

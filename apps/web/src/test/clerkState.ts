export const clerkState = {
  isLoaded: true,
  isSignedIn: false,
};

export function resetClerkState() {
  clerkState.isLoaded = true;
  clerkState.isSignedIn = false;
}

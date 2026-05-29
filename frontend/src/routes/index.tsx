import { createFileRoute, redirect } from "@tanstack/react-router";

/** Home opens Launchpad chat — avoids heavy dashboard API calls on every visit. */
export const Route = createFileRoute("/")({
  beforeLoad: () => {
    throw redirect({ to: "/interview" });
  },
});

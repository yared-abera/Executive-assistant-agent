import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ConnectionBadge } from "./ConnectionBadge";

describe("ConnectionBadge", () => {
  it("shows live when connected", () => {
    render(<ConnectionBadge connected={true} />);
    expect(screen.getByText(/live/i)).toBeInTheDocument();
  });

  it("shows offline when disconnected", () => {
    render(<ConnectionBadge connected={false} />);
    expect(screen.getByText(/offline/i)).toBeInTheDocument();
  });
});

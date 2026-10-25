import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PendingApprovals } from "./PendingApprovals";

const item = {
  id: 7,
  action_type: "book_meeting",
  title: "Approve booking",
  summary: "Book at 11:00",
  payload: {},
  status: "pending",
};

describe("PendingApprovals", () => {
  it("renders pending items and fires approve/reject", async () => {
    const user = userEvent.setup();
    const onApprove = vi.fn();
    const onReject = vi.fn();
    render(
      <PendingApprovals
        items={[item]}
        loading={false}
        error={null}
        busyId={null}
        onApprove={onApprove}
        onReject={onReject}
      />,
    );

    expect(screen.getByText("Approve booking")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^approve$/i }));
    expect(onApprove).toHaveBeenCalledWith(7);
    await user.click(screen.getByRole("button", { name: /^reject$/i }));
    expect(onReject).toHaveBeenCalledWith(7);
  });

  it("shows empty state when queue is clear", () => {
    render(
      <PendingApprovals
        items={[]}
        loading={false}
        error={null}
        busyId={null}
        onApprove={vi.fn()}
        onReject={vi.fn()}
      />,
    );
    expect(screen.getByText(/no pending actions/i)).toBeInTheDocument();
  });
});

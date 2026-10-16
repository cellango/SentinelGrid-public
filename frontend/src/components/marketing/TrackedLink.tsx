"use client";

import Link, { type LinkProps } from "next/link";
import { trackMarketingEvent, type MarketingEventName } from "@/lib/marketing/analytics";

type TrackedLinkProps = LinkProps & {
  children: React.ReactNode;
  className?: string;
  eventName?: MarketingEventName;
  eventProps?: Record<string, unknown>;
  onClick?: React.MouseEventHandler<HTMLAnchorElement>;
};

export function TrackedLink({
  children,
  className,
  eventName = "marketing_cta_click",
  eventProps,
  onClick,
  ...props
}: TrackedLinkProps) {
  return (
    <Link
      {...props}
      className={className}
      onClick={(e) => {
        trackMarketingEvent(eventName, {
          href: typeof props.href === "string" ? props.href : props.href.toString(),
          ...eventProps,
        });
        onClick?.(e);
      }}
    >
      {children}
    </Link>
  );
}

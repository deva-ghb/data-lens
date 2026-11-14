import * as RadixTabs from "@radix-ui/react-tabs";
import type { ReactNode } from "react";
import "./ui.css";

export type TabItem = { value: string; label: string; count?: number };

export type TabsProps = {
  value: string;
  onValueChange: (value: string) => void;
  tabs: TabItem[];
  label: string;
  children: ReactNode;
};

export function Tabs({ value, onValueChange, tabs, label, children }: TabsProps) {
  return (
    <RadixTabs.Root value={value} onValueChange={onValueChange}>
      <RadixTabs.List className="dl-tabs__list" aria-label={label}>
        {tabs.map((tab) => (
          <RadixTabs.Trigger key={tab.value} value={tab.value} className="dl-tabs__trigger">
            {tab.label}
            {tab.count !== undefined && <span className="dl-tabs__count">{tab.count}</span>}
          </RadixTabs.Trigger>
        ))}
      </RadixTabs.List>
      {children}
    </RadixTabs.Root>
  );
}

export function TabPanel({ value, children }: { value: string; children: ReactNode }) {
  return (
    <RadixTabs.Content value={value} className="dl-tabs__panel">
      {children}
    </RadixTabs.Content>
  );
}

"use client"

import * as React from "react"
import {
  LayoutDashboard,
  Upload,
  Flame,
  PiggyBank,
} from "lucide-react"
import Link from "next/link"
import { usePathname } from "next/navigation"

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar"

const navItems = [
  {
    title: "Dashboard",
    url: "/",
    icon: LayoutDashboard,
  },
  {
    title: "Import",
    url: "/import",
    icon: Upload,
  },
  {
    title: "Budget",
    url: "/budget",
    icon: PiggyBank,
  },
]

import { ModeToggle } from "@/components/mode-toggle"

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname()

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader className="border-b border-sidebar-border">
        <div className="flex items-center justify-between gap-2 px-2 py-3 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:px-0">
          <div className="flex items-center gap-2 overflow-hidden">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-orange-500/15 border border-orange-500/20 overflow-hidden">
              <img src="/icon.png" alt="FIRE AI Logo" className="h-full w-full object-contain" />
            </div>
            <span className="font-bold text-lg bg-gradient-to-r from-orange-500 to-orange-400 bg-clip-text text-transparent group-data-[collapsible=icon]:hidden">
              FIRE AI
            </span>
          </div>
          <div className="group-data-[collapsible=icon]:hidden">
            <ModeToggle />
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={pathname === item.url}
                    tooltip={item.title}
                  >
                    <Link href={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarRail />
    </Sidebar>
  )
}

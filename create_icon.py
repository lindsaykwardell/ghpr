#!/usr/bin/env python3
"""Generate a git-branch menu bar icon using Quartz/CoreGraphics."""

import os
import sys
import math

venv_dir = os.path.join(os.path.dirname(__file__), "venv")
for entry in os.listdir(os.path.join(venv_dir, "lib")):
    if entry.startswith("python"):
        sys.path.insert(0, os.path.join(venv_dir, "lib", entry, "site-packages"))
        break

import Quartz

ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "github.png")

size = 22
scale = 2  # @2x for retina
px = size * scale

# Create a bitmap context with alpha channel (RGBA premultiplied)
cs = Quartz.CGColorSpaceCreateDeviceRGB()
ctx = Quartz.CGBitmapContextCreate(
    None, px, px, 8, px * 4,
    cs,
    Quartz.kCGImageAlphaPremultipliedLast,
)

# Scale for retina
Quartz.CGContextScaleCTM(ctx, scale, scale)

# All drawing in 22x22 point space
# Git branch icon layout (origin bottom-left, y increases upward):
#
#   Main trunk: vertical line from bottom to top at x=9
#   Bottom node: circle at (9, 4)
#   Top node: circle at (9, 18)
#   Branch node: circle at (15, 14)
#   Branch curve: from trunk around (9, 10) curving right to (15, 14)

line_w = 1.8
node_r = 2.2  # radius of endpoint circles
trunk_x = 9.0

bottom_y = 4.0
top_y = 18.0
branch_x = 15.0
branch_y = 14.0
fork_y = 9.0  # where the branch forks off the trunk

# Set black color
Quartz.CGContextSetRGBFillColor(ctx, 0, 0, 0, 1)
Quartz.CGContextSetRGBStrokeColor(ctx, 0, 0, 0, 1)
Quartz.CGContextSetLineWidth(ctx, line_w)
Quartz.CGContextSetLineCap(ctx, Quartz.kCGLineCapRound)
Quartz.CGContextSetLineJoin(ctx, Quartz.kCGLineJoinRound)

# Draw the main trunk line (bottom to top)
Quartz.CGContextBeginPath(ctx)
Quartz.CGContextMoveToPoint(ctx, trunk_x, bottom_y)
Quartz.CGContextAddLineToPoint(ctx, trunk_x, top_y)
Quartz.CGContextStrokePath(ctx)

# Draw the branch curve from trunk to branch node
# Cubic bezier: start at (trunk_x, fork_y), end at (branch_x, branch_y)
Quartz.CGContextBeginPath(ctx)
Quartz.CGContextMoveToPoint(ctx, trunk_x, fork_y)
Quartz.CGContextAddCurveToPoint(
    ctx,
    trunk_x, fork_y + 2.5,       # control point 1
    branch_x - 2.0, branch_y,    # control point 2
    branch_x, branch_y,           # end point
)
Quartz.CGContextStrokePath(ctx)

# Draw circles at the three nodes (filled)
for (cx, cy) in [(trunk_x, bottom_y), (trunk_x, top_y), (branch_x, branch_y)]:
    Quartz.CGContextBeginPath(ctx)
    Quartz.CGContextAddArc(ctx, cx, cy, node_r, 0, 2 * math.pi, 0)
    Quartz.CGContextFillPath(ctx)

# Generate image and save as PNG
image = Quartz.CGBitmapContextCreateImage(ctx)
url = Quartz.CFURLCreateFromFileSystemRepresentation(
    None, ICON_PATH.encode("utf-8"), len(ICON_PATH.encode("utf-8")), False
)
dest = Quartz.CGImageDestinationCreateWithURL(url, "public.png", 1, None)
Quartz.CGImageDestinationAddImage(dest, image, None)
Quartz.CGImageDestinationFinalize(dest)

print(f"Icon saved to {ICON_PATH} ({px}x{px} pixels, {size}x{size} points @2x)")

# --- App icon (512x512) for notifications ---
APP_ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.png")
app_size = 512

app_cs = Quartz.CGColorSpaceCreateDeviceRGB()
app_ctx = Quartz.CGBitmapContextCreate(
    None, app_size, app_size, 8, app_size * 4,
    app_cs,
    Quartz.kCGImageAlphaPremultipliedLast,
)

# Rounded-rect purple background
corner_radius = 90.0
bg_rect = Quartz.CGRectMake(0, 0, app_size, app_size)
bg_path = Quartz.CGPathCreateWithRoundedRect(bg_rect, corner_radius, corner_radius, None)
Quartz.CGContextSetRGBFillColor(app_ctx, 0.38, 0.15, 0.71, 1.0)  # purple (#6127B5)
Quartz.CGContextAddPath(app_ctx, bg_path)
Quartz.CGContextFillPath(app_ctx)

# White git-branch symbol scaled to 512x512
s = app_size / 22.0  # scale factor from 22pt design space

Quartz.CGContextSetRGBFillColor(app_ctx, 1, 1, 1, 1)
Quartz.CGContextSetRGBStrokeColor(app_ctx, 1, 1, 1, 1)
Quartz.CGContextSetLineWidth(app_ctx, line_w * s)
Quartz.CGContextSetLineCap(app_ctx, Quartz.kCGLineCapRound)
Quartz.CGContextSetLineJoin(app_ctx, Quartz.kCGLineJoinRound)

# Trunk
Quartz.CGContextBeginPath(app_ctx)
Quartz.CGContextMoveToPoint(app_ctx, trunk_x * s, bottom_y * s)
Quartz.CGContextAddLineToPoint(app_ctx, trunk_x * s, top_y * s)
Quartz.CGContextStrokePath(app_ctx)

# Branch curve
Quartz.CGContextBeginPath(app_ctx)
Quartz.CGContextMoveToPoint(app_ctx, trunk_x * s, fork_y * s)
Quartz.CGContextAddCurveToPoint(
    app_ctx,
    trunk_x * s, (fork_y + 2.5) * s,
    (branch_x - 2.0) * s, branch_y * s,
    branch_x * s, branch_y * s,
)
Quartz.CGContextStrokePath(app_ctx)

# Node circles
for (cx, cy) in [(trunk_x, bottom_y), (trunk_x, top_y), (branch_x, branch_y)]:
    Quartz.CGContextBeginPath(app_ctx)
    Quartz.CGContextAddArc(app_ctx, cx * s, cy * s, node_r * s, 0, 2 * math.pi, 0)
    Quartz.CGContextFillPath(app_ctx)

# Save app icon
app_image = Quartz.CGBitmapContextCreateImage(app_ctx)
app_url = Quartz.CFURLCreateFromFileSystemRepresentation(
    None, APP_ICON_PATH.encode("utf-8"), len(APP_ICON_PATH.encode("utf-8")), False
)
app_dest = Quartz.CGImageDestinationCreateWithURL(app_url, "public.png", 1, None)
Quartz.CGImageDestinationAddImage(app_dest, app_image, None)
Quartz.CGImageDestinationFinalize(app_dest)

print(f"App icon saved to {APP_ICON_PATH} ({app_size}x{app_size} pixels)")

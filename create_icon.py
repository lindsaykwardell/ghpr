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

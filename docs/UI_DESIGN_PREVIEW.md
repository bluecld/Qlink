# Web UI v2 - Visual Design Preview

## Header Section
```
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║                    VANTAGE CONTROL                               ║
║           (purple/indigo gradient text effect)                   ║
║                                                                  ║
║              ● System Online  |  Updated: 14:35:42               ║
║           (green pulsing dot)    (real-time timestamp)           ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

## Controls Bar
```
┌──────────────────┐  ┌──────────────────────┐
│ Jump to Floor... │  │ Expand/Collapse All  │
└──────────────────┘  └──────────────────────┘
   (dropdown menu)      (toggle button)
```

## Floor Section (Collapsible)
```
╔════════════════════════════════════════════════════════════════════╗
║  🔽  1ST FLOOR                                                     ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  ┌─────────────────────────────────────────────────────────────┐  ║
║  │  GAME ROOM                              [All Off]            │  ║
║  ├─────────────────────────────────────────────────────────────┤  ║
║  │                                                              │  ║
║  │  ROOM SCENES                                                 │  ║
║  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                       │  ║
║  │  │  On  │ │Medium│ │ Dim  │ │ Off  │                       │  ║
║  │  └──────┘ └──────┘ └──────┘ └──────┘                       │  ║
║  │  (active button highlighted in purple gradient)              │  ║
║  │                                                              │  ║
║  │  ────────────────────────────────────────────────────────   │  ║
║  │                                                              │  ║
║  │  Pendant                               Level: 75%           │  ║
║  │  ═════════●════════                    [ON] [OFF]           │  ║
║  │  (purple gradient slider)                                   │  ║
║  │                                                              │  ║
║  │  Soffit                                Level: 60%           │  ║
║  │  ══════●═══════════                    [ON] [OFF]           │  ║
║  │                                                              │  ║
║  │  Pool Table                            Level: 100%          │  ║
║  │  ═════════════════●                    [ON] [OFF]           │  ║
║  │                                                              │  ║
║  └─────────────────────────────────────────────────────────────┘  ║
║                                                                    ║
║  ┌─────────────────────────────────────────────────────────────┐  ║
║  │  LIBRARY                                [All Off]            │  ║
║  ├─────────────────────────────────────────────────────────────┤  ║
║  │                                                              │  ║
║  │  ROOM SCENES                                                 │  ║
║  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                       │  ║
║  │  │  On  │ │Medium│ │ Dim  │ │ Off  │                       │  ║
║  │  └──────┘ └──────┘ └──────┘ └──────┘                       │  ║
║  │                                                              │  ║
║  │  Entry Lights                          Level: 0%            │  ║
║  │  ●══════════════════                   [ON] [OFF]           │  ║
║  │                                                              │  ║
║  │  Library Lights                        Level: 45%           │  ║
║  │  ═════●═════════════                   [ON] [OFF]           │  ║
║  │                                                              │  ║
║  └─────────────────────────────────────────────────────────────┘  ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
```

## Color Scheme

### Background
- Base: Dark blue gradient (#1a1a2e → #16213e)
- Cards: Semi-transparent white (5% opacity) with blur
- Borders: Subtle white (10% opacity)

### Accent Colors
- Primary: Purple gradient (#667eea → #764ba2)
- Success (ON): Green gradient (#10b981 → #059669)
- Neutral (OFF): Gray gradient (#64748b → #475569)
- Error: Red (#ef4444)
- Warning: Yellow (#f59e0b)

### Text
- Primary: Light gray (#e4e4e4)
- Secondary: Muted gray (#cbd5e1)
- Accent: Light purple (#c7d2fe)
- Dim: Slate (#94a3b8)

## Interactive Elements

### Scene Buttons
```
┌────────────────┐
│    Medium      │  ← Inactive: rgba(102, 126, 234, 0.2)
└────────────────┘

┌────────────────┐
│  ★  Dim  ★     │  ← Active: Purple gradient with glow
└────────────────┘     Highlighted, raised shadow effect
```

### Load Controls
```
Pendant                               Level: 75%
═════════●════════                    [ON] [OFF]
          ↑
    Purple gradient thumb
    Glows on hover
    Smooth drag interaction
```

### Status Indicator
```
  ● System Online
  ↑
Green pulsing dot
Animated breathing effect
Changes color based on connection:
  Green  = Online
  Yellow = Warning
  Red    = Offline
```

### Toast Notifications
```
┌──────────────────────────────────┐
│  ✓  Game Room: Medium            │
└──────────────────────────────────┘
   ↑
Slides up from bottom-right
Green background (success)
Disappears after 3 seconds
```

## Responsive Design

### Desktop (>768px)
- Cards in grid: 2-3 columns
- Full controls visible
- Side-by-side buttons

### Tablet/Mobile (<768px)
- Cards stack: 1 column
- Controls stack vertically
- Touch-optimized button sizes
- Larger sliders for finger control

## Animations

1. **Page Load**
   - Cards fade in with stagger
   - Smooth entrance from bottom

2. **Floor Expand/Collapse**
   - Smooth height transition (0.3s)
   - Arrow rotates -90° when collapsed

3. **Button Press**
   - Slight scale-up on hover (1.05x)
   - Translate up 2px
   - Shadow increases
   - Active state glows

4. **Slider Interaction**
   - Thumb scales 1.2x on hover
   - Shadow intensifies
   - Smooth value transition

5. **Status Updates**
   - Level text fades in
   - Slider animates to new position
   - Subtle pulse on change

## Key Design Features

✨ **Glassmorphism** - Semi-transparent cards with backdrop blur
🎨 **Gradient Accents** - Purple/indigo theme throughout
🌊 **Smooth Animations** - 0.3s transitions everywhere
💡 **Visual Feedback** - Every action shows immediate response
📱 **Mobile-First** - Touch-friendly, responsive grid
🔄 **Real-time Updates** - Polling every 10 seconds
⚡ **Performance** - Only visible loads polled
🎯 **Accessibility** - High contrast, clear labels

## Comparison to Original UI

| Feature | Original | v2 Dark Theme |
|---------|----------|---------------|
| Theme | Light purple gradient | Dark blue with glassmorphism |
| Scene Control | None | Full button/scene support |
| Polling | None | Every 10 seconds |
| Load Status | Not shown | Real-time level display |
| Visual Design | Simple, functional | Modern, sleek, polished |
| Animations | Minimal | Smooth throughout |
| Mobile | Basic responsive | Fully optimized |
| Feedback | Basic toasts | Enhanced with colors |

## Try It Out

When Pi is online, access at:
```
http://192.168.1.213:8000/ui/home-v2.html
```

Compare to original:
```
http://192.168.1.213:8000/ui/home.html
```

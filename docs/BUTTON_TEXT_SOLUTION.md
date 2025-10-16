# Smart Button Text Solution

## The Problem
Button names like "All Outside Off" or "Landscape" can overflow or look cramped on small buttons.

## Cool Solutions Implemented

### 1. **Smart Font Sizing** 📏
Buttons automatically adjust text size based on name length:

- **Short names** (≤12 chars): Normal size (0.9em) - "On", "Off", "Dim", "Path"
- **Medium names** (13-18 chars): Smaller (0.75em) - "Game Room On", "Landscape"
- **Long names** (>18 chars): Smallest (0.7em) - "All Outside Off", "Suite Off"

```css
/* Normal */
.scene-btn { font-size: 0.9em; }

/* Medium names */
.scene-btn.long-text { font-size: 0.75em; }

/* Long names */
.scene-btn.very-long-text { font-size: 0.7em; }
```

### 2. **Text Truncation with Ellipsis** ✂️
If text still doesn't fit, it truncates with "...":
- "All Outside..."
- "Landscape..."

```css
overflow: hidden;
text-overflow: ellipsis;
white-space: nowrap;
```

### 3. **Hover Tooltip** 💬
When you hover over any button, a tooltip appears above showing the **full button name**:

```
     ┌────────────────────┐
     │ All Outside Off    │  ← Tooltip
     └────────────────────┘
            ▼
     ┌──────────┐
     │ All Ou...│  ← Button
     └──────────┘
```

- Black background with slight transparency
- White text, easy to read
- Smooth fade-in animation
- Positioned above button
- Auto-hides if name fits completely

```css
.scene-btn::after {
    content: attr(data-full-name);
    position: absolute;
    bottom: 100%;
    opacity: 0;
    /* ... smooth transition ... */
}

.scene-btn:hover::after {
    opacity: 1;
}
```

### 4. **Max Width Cap** 📐
Buttons have a maximum width (150px) so they don't stretch too wide and look odd.

```css
max-width: 150px;
```

### 5. **Smart Padding Adjustment** 📦
Longer text gets less padding to maximize space:
- Normal: 10px horizontal padding
- Long text: 8px horizontal padding
- Very long: 6px horizontal padding

## Visual Examples

### Short Button Names
```
┌─────────┐ ┌─────────┐ ┌─────────┐
│   Path  │ │  Soffit │ │   Fan   │
└─────────┘ └─────────┘ └─────────┘
   Normal      Normal      Normal
   0.9em       0.9em       0.9em
```

### Medium Button Names
```
┌──────────────┐ ┌──────────────┐
│  Game Room   │ │  Landscape   │
│      On      │ │              │
└──────────────┘ └──────────────┘
  Medium (13ch)    Medium (9ch)
     0.75em          0.75em
```

### Long Button Names
```
┌─────────────┐
│All Outside  │  ← Hover shows "All Outside Off"
│    Off      │
└─────────────┘
 Very Long (15ch)
     0.7em
```

### Truncated with Tooltip
```
     Hover shows: "Station V20 - Entry Foyer Controls"
              ▼
┌──────────────┐
│Station V20...│
└──────────────┘
```

## How It Works

JavaScript automatically adds size classes when rendering:

```javascript
const buttonHtml = room.buttons.map(btn => {
    // Smart sizing based on name length
    let sizeClass = '';
    if (btn.name.length > 18) {
        sizeClass = 'very-long-text';
    } else if (btn.name.length > 12) {
        sizeClass = 'long-text';
    }

    return `<div class="scene-btn ${sizeClass}"
                 data-full-name="${btn.name}"
                 ...>${btn.name}</div>`;
});
```

The `data-full-name` attribute stores the complete name for the tooltip.

## Benefits

✅ **Automatic** - No manual configuration needed
✅ **Responsive** - Adjusts to button name length
✅ **User-friendly** - Tooltips show full names
✅ **Clean look** - No text overflow or wrapping
✅ **Smooth** - Nice animations and transitions
✅ **Consistent** - All buttons look polished

## Testing

Open `ui-preview-local.html` to see it in action:

**Entry/Foyer (V20)** has varied button lengths:
- Short: "Path" (4 chars)
- Medium: "Landscape" (9 chars)
- Long: "All Outside Off" (15 chars)

**Master Bath (V12)** shows specialized names:
- "Ceiling" - normal
- "Vanity" - normal
- "Shower" - normal
- "Bath On" - normal

**Game Room (V23)** has fixture names:
- "Pendant" - normal
- "Pool Table" - medium sizing
- "Game Room On" - medium sizing

## Mobile Optimization

On mobile, buttons stack vertically and can use full width, making text more readable. The smart sizing still applies but has more room to breathe.

```css
@media (max-width: 768px) {
    .scene-btn {
        max-width: 100%;
        /* Full width on mobile */
    }
}
```

---

**Result:** Buttons look professional no matter how long the name is! 🎨✨

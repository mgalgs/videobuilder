# Redrawing product UI

Use a capture when it shows the real product clearly. Redraw as vector UI
when staging banners, build IDs, blank thumbnails or unusable resolution
would distract from the story. Work from a real screen or approved design:
keep its actual copy, colours, hierarchy and controls. Simplify incidental
detail for legibility; do not invent features or fabricate product results.
Vendor any reference assets before rendering.

Choose a design width in CSS px for each format's composition. For a panel
`box`, use `u = box.w / design_width`: multiply CSS sizes, spacing, radii and
font sizes by `u`. Recompose a wide screen for portrait before choosing this
unit, rather than squeezing the whole desktop screen into it.

Keep each reusable block in a module or object with `height(w)` and
`draw(cv, box)`. Measure wrapped text with the same font, width and unit used
by draw. Build the layout once per format:

```python
blocks = [Header(), Summary(), ResultList()]
boxes, total = panel.stack((block.height(panel.w) for block in blocks),
                          gap=16 * u, align='top')
# Cache blocks and boxes in that format's layout table.
for block, box in zip(blocks, boxes):
    block.draw(cv, box)
```

`Box.stack` returns full-width boxes and the occupied height, including gaps
only between blocks. Center/bottom alignment uses spare height; overflowing
stacks stay at the top without shrinking. Use `total` to check the panel fits
or size its background; do not measure all the blocks again. Mark meaningful
content and inspect cut sheets: a panel outline alone is not a populated UI.

## Brief overview

This Cline rule file captures project-specific preferences for the Jekyll blog, including visual preferences, tool usage guidelines, and category page guidelines.

## Design Preferences

-   Prioritize a modern and clean look.
-   Pay attention to subtle visual details like borders and shadows.
-   Use the accent color to highlight key elements.

## Header Styling

-   Add a subtle bottom border to the header using the accent color.
-   Incorporate a shadow effect for depth.

## Tool Usage

-   Do not use the terminal.
-   Use write_to_file for creating new files or overwriting entire files.
-   Use replace_in_file for targeted edits to existing files.

## Category Pages

-   Category files should be named after the category they represent.
    -   Example: `recenzje.html` for the "recenzje" category.
-   Category files should have a YAML front matter with the following structure:
    ```yaml
    ---
    layout: category
    permalink: /category/[category-name]/
    category: [category-name]
    ---
    ```
    -   Replace `[category-name]` with the actual category name.
-   The `category` layout should be used for category pages.

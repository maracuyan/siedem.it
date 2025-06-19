## Brief overview

This Cline rule file provides guidelines for creating and maintaining category pages in the Jekyll blog.

## File Naming

*   Category files should be named after the category they represent.
    *   Example: `recenzje.html` for the "recenzje" category.

## File Structure

*   Category files should have a YAML front matter with the following structure:

    ```yaml
    ---
    layout: category
    permalink: /category/[category-name]/
    category: [category-name]
    ---
    ```

    *   Replace `[category-name]` with the actual category name.

## Category Layout

*   The `category` layout should be used for category pages.

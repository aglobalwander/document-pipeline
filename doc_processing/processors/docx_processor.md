# DOCX to Markdown Conversion Plan

## Implementation Approach

1. **Use Native Mammoth Markdown Conversion**
   - Replace `convert_to_html()` with `convert_to_markdown()`
   - This provides better native Markdown support

2. **Style Mapping**
```python
style_map = '''
p[style-name='Heading 1'] => h1: $1
p[style-name='Heading 2'] => h2: $1
p[style-name='Heading 3'] => h3: $1
p[style-name='Heading 4'] => h4: $1
p[style-name='Heading 5'] => h5: $1
p[style-name='Heading 6'] => h6: $1
p[style-name='Title'] => h1: $1
p[style-name='Subtitle'] => h2: $1
r[style-name='Strong'] => **$1**
r[style-name='Emphasis'] => *$1*
'''
```

3. **Error Handling**
   - Add try/catch blocks for file operations
   - Log conversion warnings and errors

4. **Post-Processing**
   - Clean up any remaining HTML tags
   - Ensure proper line breaks
   - Validate Markdown syntax

5. **Validation**
   - Check output is valid Markdown
   - Verify headings and formatting preserved

## Testing Plan

1. Test with various DOCX files:
   - Simple documents
   - Complex layouts
   - Tables and images
   - Different heading styles

2. Verify:
   - Headings converted correctly
   - Formatting preserved
   - No residual HTML
   - Proper line breaks
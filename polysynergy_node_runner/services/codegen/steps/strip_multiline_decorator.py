def strip_multiline_decorator(lines, decorator="@node("):
    inside = False
    paren_count = 0
    for line in lines:
        st = line.strip()

        if not inside:
            if st.startswith(decorator):
                opens = st.count("(")
                closes = st.count(")")
                if opens == closes:
                    continue
                else:
                    inside = True
                    paren_count = opens - closes
            else:
                yield line
        else:
            opens = line.count("(")
            closes = line.count(")")
            paren_count += (opens - closes)
            if paren_count <= 0:
                inside = False
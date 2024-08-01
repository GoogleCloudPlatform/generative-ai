"""This module is the page for generating CSS """

# pylint: disable=line-too-long, invalid-name, import-error, use-dict-literal, invalid-name
# Add footer
footer = """<style>
a:link , a:visited{
color: blue;
background-color: transparent;
text-decoration: underline;
}

a:hover,  a:active {
color: red;
background-color: transparent;
text-decoration: underline;
}

.footer {
position: fixed;
left: 0;
bottom: 0;
width: 100%;
background-color: white;
color: black;
text-align: center;
}
</style>
<div class="footer">
<p><i>Powered By</i>   <a style='display: block; text-align: center;' href="https://cloud.google.com/spanner/?hl=en" target="_blank">Google Cloud Spanner</a></p>
</div>
"""

favicon = "images/small-logo.png"

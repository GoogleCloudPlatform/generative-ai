module.exports = {
  ...require('gts/.prettierrc.json'),
  "overrides": [
    {
      "files": "*.html",
      "options": {
        "parser": "angular"
      }
    },
    {
      "files": "*.scss",
      "options": {
        "parser": "scss"
      }
    }
  ]
}

/*Package cmd is for cmd
Copyright © 2019 Toomore Chiang

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
*/
package cmd

import (
	"github.com/spf13/cobra"
	"github.com/spf13/cobra/doc"
)

var (
	docsBash     bool
	docsMarkdown bool
)

// docsCmd represents the docs command
var docsCmd = &cobra.Command{
	Use:   "docs",
	Short: "To generate cmd document",
	Long:  `To generate Markdown document.`,
	Run: func(cmd *cobra.Command, args []string) {
		if docsBash {
			rootCmd.GenBashCompletionFile("./mail_sender")
			cmd.Println("Gen Bash Completion File ...")
		}
		if docsMarkdown {
			doc.GenMarkdownTree(rootCmd, "./")
			cmd.Println("Gen Markdown Tree ...")
		}
	},
}

func init() {
	rootCmd.AddCommand(docsCmd)

	docsCmd.Flags().BoolVarP(&docsBash, "bash", "b", false, "generate bash-completion")
	docsCmd.Flags().BoolVarP(&docsMarkdown, "markdown", "m", false, "generate Markdown docs")
}

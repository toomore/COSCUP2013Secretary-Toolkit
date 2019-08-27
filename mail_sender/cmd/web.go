/*Package cmd is for cmd
Copyright © 2019 Toomore Chiang

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/
package cmd

import (
	"fmt"
	"log"
	"mail_sender/queue"

	"github.com/gin-gonic/gin"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

// webCmd represents the web command
var webCmd = &cobra.Command{
	Use:   "web",
	Short: "a web to recive queue requests",
	Long:  `To recive queue requests and send to RabbitMQ.`,
	PreRun: func(cmd *cobra.Command, args []string) {
		mq = queue.New(viper.GetString("rabbitmq.url"))
		exchanges := viper.GetStringSlice("rabbitmq.exchanges")
		for i := 0; i < len(exchanges); i++ {
			mq.DeclareExchange(exchanges[i])
		}

		queues := viper.GetStringSlice("rabbitmq.queues")
		for i := 0; i < len(queues); i++ {
			q := viper.GetStringMapString("rabbitmq." + queues[i])
			mq.DeclareQueue(q["name"])
			mq.Exchange[q["bind"]].BindQueue(q["name"], q["route"])
		}
	},
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("web called")

		r := gin.Default()
		r.GET("/ping", func(c *gin.Context) {
			c.JSON(200, gin.H{
				"message": "pong",
			})
		})

		r.POST("/exchange/:exchange/:key", func(c *gin.Context) {
			body := c.PostForm("body")
			exchange := c.Param("exchange")
			key := c.Param("key")
			log.Println(viper.GetStringMapString("ses"))
			if _, ok := mq.Exchange[exchange]; ok {
				mq.Exchange[exchange].Publish(key, []byte(body))
			}

			c.JSON(200, gin.H{
				"exchange": exchange,
				"body":     body,
			})
		})

		r.Run("127.0.0.1:7700") // listen and serve on 0.0.0.0:8080
	},
}

func init() {
	rootCmd.AddCommand(webCmd)

	// Here you will define your flags and configuration settings.

	// Cobra supports Persistent Flags which will work for this command
	// and all subcommands, e.g.:
	// webCmd.PersistentFlags().String("foo", "", "A help for foo")

	// Cobra supports local flags which will only run when this command
	// is called directly, e.g.:
	// webCmd.Flags().BoolP("toggle", "t", false, "Help message for toggle")
}

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
	"os"
	"os/signal"
	"syscall"

	"github.com/spf13/cobra"
	"github.com/streadway/amqp"
)

func consumerCmdRun(cmd *cobra.Command, args []string) {
	initMQ()
	fmt.Println("consumer called")
	secretaryQueue := mq.GetConsumer("secretary")

	quit := make(chan struct{}, 1)

	quota := getSendQuota()
	log.Println("[info]", "MaxSendRate", *quota.MaxSendRate)
	maxRate := int(*quota.MaxSendRate)
	limit := make(chan struct{}, maxRate)
	mq.Channel.Qos(maxRate, 0, false)

	// --- signal
	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs, syscall.SIGINT, syscall.SIGTERM, syscall.SIGKILL)

	// --- Notify Close
	notifyClose := mq.Conn.NotifyClose(make(chan *amqp.Error))
	var restart bool

	go func() {
		for {
			select {
			case sig := <-sigs:
				log.Println("sig:", sig)
				quit <- struct{}{}
				return
			case n := <-notifyClose:
				log.Println("sig.close:", n)
				restart = true
				quit <- struct{}{}
				return
			case t := <-secretaryQueue:
				limit <- struct{}{}
				log.Println(t.MessageId)
				go sender(t, limit, maxRate)
			}
		}
	}()
	<-quit
	log.Printf("quit: %+v", mq)
	if restart == true {
		log.Println("Prepare restart ...")
		consumerCmdRun(cmd, args)
	}
}

// consumerCmd represents the consumer command
var consumerCmd = &cobra.Command{
	Use:   "consumer",
	Short: "consumer for worker",
	Long:  `Create a consumer for worker`,
	PreRun: func(cmd *cobra.Command, args []string) {
		initSES()
	},
	Run: consumerCmdRun,
}

func init() {
	rootCmd.AddCommand(consumerCmd)

	// Here you will define your flags and configuration settings.

	// Cobra supports Persistent Flags which will work for this command
	// and all subcommands, e.g.:
	// consumerCmd.PersistentFlags().String("foo", "", "A help for foo")

	// Cobra supports local flags which will only run when this command
	// is called directly, e.g.:
	// consumerCmd.Flags().BoolP("toggle", "t", false, "Help message for toggle")
}

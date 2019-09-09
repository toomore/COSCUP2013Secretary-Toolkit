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

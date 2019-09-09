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
	"log"
	"mail_sender/queue"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/credentials"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/ses"
	"github.com/spf13/viper"
	"github.com/streadway/amqp"
)

func initMQ() {
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
}

func initSES() {
	svc = ses.New(session.Must(session.NewSession(
		&aws.Config{
			Region: aws.String(viper.GetString("ses.region")),
			Credentials: credentials.NewStaticCredentials(
				viper.GetString("ses.id"), viper.GetString("ses.secret"), ""),
		},
	),
	))
}

func getSendQuota() *ses.GetSendQuotaOutput {
	result, err := svc.GetSendQuota(&ses.GetSendQuotaInput{})
	if err != nil {
		log.Println("[ERR]", err)
	}
	return result
}

func sender(t amqp.Delivery, limit chan struct{}, retry int) {
	raw := &ses.RawMessage{}
	raw.SetData(t.Body)
	if err := raw.Validate(); err != nil {
		log.Println("[sender.Validate]", err)
		t.Ack(false)
		<-limit
		return
	}

	input := &ses.SendRawEmailInput{RawMessage: raw}

	for i := 0; i < retry; i++ {
		output, err := svc.SendRawEmail(input)
		if err == nil {
			log.Println("[sender.OK]", i, t.MessageId, output.String(), err)
			t.Ack(false)
			<-limit
			return
		}
		log.Println("[sender.FAIL]", i, t.MessageId, output.String(), err)
	}
	t.Nack(false, false)
	<-limit
}

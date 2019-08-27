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

func sender(t amqp.Delivery, limit chan struct{}) {
	raw := &ses.RawMessage{}
	raw.SetData(t.Body)
	log.Println(raw.Validate())

	input := &ses.SendRawEmailInput{}
	input.RawMessage = raw

	for i := 0; i < 7; i++ {
		output, err := svc.SendRawEmail(input)
		if err == nil {
			log.Println("[OK]", i, output.String(), err)
			t.Ack(false)
			return
		}
		log.Println("[FAIL]", i, output.String(), err)
	}
	t.Nack(false, false)
	<-limit
}

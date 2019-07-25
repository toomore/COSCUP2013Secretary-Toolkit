package main

import (
	"encoding/csv"
	"flag"
	"fmt"
	"log"
	"os"
	"sync"

	plivo "github.com/plivo/plivo-go"
	"github.com/spf13/viper"
)

var (
	clientOption = &plivo.ClientOptions{}
	client       *plivo.Client
	wg           sync.WaitGroup

	path   = flag.String("p", "", "CSV file path")
	dryRun = flag.Bool("d", false, "Dry run for test")
)

func init() {
	var err error

	viper.SetConfigName("config")
	viper.AddConfigPath(".")
	err = viper.ReadInConfig()

	if err != nil {
		panic(fmt.Errorf("Fatal error config file: %s \n", err))
	}
	client, err = plivo.NewClient(
		viper.GetString("plivo.id"), viper.GetString("plivo.token"), clientOption)
	if err != nil {
		log.Fatal(err)
	}
}

func sms(no int, src, dst, text string) {
	defer wg.Done()
	if *dryRun {
		log.Printf("[DryRun] %02d %s %s", no, dst, text)
	} else {
		resp, err := client.Messages.Create(plivo.MessageCreateParams{
			Src:  src,
			Dst:  dst,
			Text: text,
		})
		if err != nil {
			log.Println("[ERROR]", no, dst, err)
		}
		log.Printf("%02d %s > %+v\n", no, dst, resp)
	}
}

func main() {
	flag.Parse()
	if *path == "" {
		log.Println("No csv file path")
		return
	}
	file, err := os.Open(*path)
	if err != nil {
		log.Fatal("Open csv fail", err)
	}
	reader := csv.NewReader(file)
	record, err := reader.ReadAll()
	if err != nil {
		log.Fatal("Read csv fail", err)
	}
	file.Close()

	var text string
	wg.Add(len(record) - 1)
	src := viper.GetString("plivo.number")
	for i, v := range record {
		if i == 0 {
			text = v[0]
			continue
		}
		log.Println(i, v)
		go sms(i, src, v[0], text)
	}
	wg.Wait()
}

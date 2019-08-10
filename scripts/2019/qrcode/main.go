package main

import (
	"encoding/csv"
	"flag"
	"fmt"
	"image/png"
	"log"
	"os"
	"strings"

	"github.com/boombuler/barcode"
	"github.com/boombuler/barcode/qr"
)

var (
	size   = flag.Int("s", 600, "PNG size")
	q      = flag.String("q", "M", "L(7%), M(15%), Q(25%), H(30%)")
	path   = flag.String("f", "", "CSV file path")
	folder = flag.String("o", "", "output folder")

	qm = map[string]qr.ErrorCorrectionLevel{
		"L": qr.L,
		"M": qr.M,
		"Q": qr.Q,
		"H": qr.H,
	}
)

// User struct
type User struct {
	Name     string
	Token    string
	Email    string
	URL      string
	FileNmae string
}

func readCSV(path string) []*User {
	file, err := os.Open(path)
	if err != nil {
		log.Fatal(err)
	}
	csvReader := csv.NewReader(file)
	data, err := csvReader.ReadAll()
	if err != nil {
		log.Fatal(err)
	}
	result := make([]*User, len(data)-1)
	for i := 1; i < len(data); i++ {
		result[i-1] = &User{}
	}
	for t, v := range data[0] {
		if v == "name" {
			for i := 1; i < len(data); i++ {
				result[i-1].Name = strings.TrimSpace(data[i][t])
			}
		}
		if v == "token" {
			for i := 1; i < len(data); i++ {
				result[i-1].Token = strings.TrimSpace(data[i][t])
			}
		}
		if v == "mail" {
			for i := 1; i < len(data); i++ {
				result[i-1].Email = strings.TrimSpace(data[i][t])
			}
		}
		if v == "url" {
			for i := 1; i < len(data); i++ {
				result[i-1].URL = strings.TrimSpace(data[i][t])
			}
		}
		if v == "filename" {
			for i := 1; i < len(data); i++ {
				result[i-1].FileNmae = strings.TrimSpace(data[i][t])
			}
		}
	}
	for i := range result {
		if result[i].FileNmae == "" {
			result[i].FileNmae = result[i].Token
		}
	}
	return result
}

func main() {
	flag.Parse()
	if *path == "" {
		log.Fatalln("No csv path")
	}
	if *folder == "" {
		log.Fatalln("No folder to output")
	}
	if err := os.Mkdir(*folder, os.ModePerm); err != nil {
		log.Println(err)
	}
	userData := readCSV(*path)

	for i := 0; i < len(userData); i++ {
		content := userData[i].Token

		// Create the barcode
		qrCode, err := qr.Encode(content, qm[*q], qr.Unicode)
		if err != nil {
			log.Fatal(err)
		}

		// Scale the barcode to size*size pixels
		qrCode, err = barcode.Scale(qrCode, *size, *size)
		if err != nil {
			log.Fatal(err)
		}

		// create the output file
		file, err := os.Create(fmt.Sprintf("./%s/%s.png", *folder, userData[i].FileNmae))
		if err != nil {
			log.Fatal(err)
		}

		// encode the barcode as png
		png.Encode(file, qrCode)

		file.Close()
	}
}

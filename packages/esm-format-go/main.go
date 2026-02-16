package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"

	"github.com/ctessum/EarthSciSerialization/packages/esm-format-go/pkg/esm"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: esm-go <command> [args]")
		fmt.Println("Commands:")
		fmt.Println("  validate <file>  - Validate an ESM file")
		fmt.Println("  convert <file>   - Convert ESM file format")
		os.Exit(1)
	}

	command := os.Args[1]
	switch command {
	case "validate":
		if len(os.Args) < 3 {
			log.Fatal("Usage: esm-go validate <file>")
		}
		validateFile(os.Args[2])
	case "convert":
		if len(os.Args) < 3 {
			log.Fatal("Usage: esm-go convert <file>")
		}
		convertFile(os.Args[2])
	default:
		log.Fatalf("Unknown command: %s", command)
	}
}

func validateFile(filename string) {
	data, err := os.ReadFile(filename)
	if err != nil {
		log.Fatalf("Failed to read file: %v", err)
	}

	var esmData esm.EsmFile
	if err := json.Unmarshal(data, &esmData); err != nil {
		log.Fatalf("Failed to parse ESM file: %v", err)
	}

	if err := esmData.Validate(); err != nil {
		log.Fatalf("Validation failed: %v", err)
	}

	fmt.Printf("File %s is valid\n", filename)
}

func convertFile(filename string) {
	data, err := os.ReadFile(filename)
	if err != nil {
		log.Fatalf("Failed to read file: %v", err)
	}

	var esmData esm.EsmFile
	if err := json.Unmarshal(data, &esmData); err != nil {
		log.Fatalf("Failed to parse ESM file: %v", err)
	}

	output, err := json.MarshalIndent(esmData, "", "  ")
	if err != nil {
		log.Fatalf("Failed to marshal ESM file: %v", err)
	}

	fmt.Println(string(output))
}
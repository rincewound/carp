#include "carp.h"
#include <iostream>
#include <fstream>

uint32_t bytes_written = 0;

class consoleWriter: public carp::IWriter
{
public:
    char buffer[100];

    void write(const char* data, size_t size) override
    {
        std::cout << data;
        memcpy(buffer + bytes_written, data, size);
        bytes_written += size;
        
    }

    void begin_frame() override
    {

    };

    void end_frame() override
    {
        std::cout << std::endl;
    }
};

void dumpBytesToFile(const std::string& filePath, const char* bytes, size_t size) {
    std::ofstream file(filePath, std::ios::binary);
    if (file.is_open()) {
        file.write(bytes, size);
        file.close();
    }
}

void main()
{
    consoleWriter w;

    //carp::setup_logging(w);
    carp::setup_logging(&w);
    //carp::write(w, 10, 20, 30, 99, 101, 33, 44);    
    std::cout << std::endl;
    CARP_DFMT("Hello World {}", 1, 6, 10, "foo", 47.1f) 
    CARP_LOG("Meh!{}", 27);
    //CARP_DFMT("Go To Hell, sucker {} ...", 1, 7, 10, "foo", 47.1f) 
    //CARP_DFMT(10,20, 44, 45);
    std::cout << std::endl;
    std::cout << bytes_written;

    // dump writer buffer to file:
    dumpBytesToFile("./data.bin", (char*)w.buffer, bytes_written);

}
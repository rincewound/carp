#ifndef CARP_H
#define CARP_H

#include <string>
#include <cstdint>
#include <optional>
#include <cassert>

namespace carp
{
    enum class Severity
    {
        Verbose,
        Info,
        Warning,
        Error
    };

    class IWriter
    {
        public:
            virtual ~IWriter() = default;             
            virtual void write(const char* data, size_t size) = 0;
            /**
             * @brief Called before starting to write data 
             *        to the writer. Use this to perform any
             *        required setup (e.g. clearing buffers,
             *        taking mutexts or similar)
             */
            virtual void begin_frame() = 0;

            /**
             * @brief Called when all data was written
             *        for a given frame. Use this do 
             *        any required cleanup work, e.g.
             *        flushing buffers, releasing mutexes...
             */
            virtual void end_frame() = 0;
    };

    class ITimeStampProvider
    {
        public:
            virtual ~ITimeStampProvider() = default;
            /**
             * @brief Provide a 32bit timestamp-like value that is
             *        added to all messages. The value is used to
             *        sort messages by time. If no timesource is 
             *        available, this function should return 0 or
             *        simply count upwards.
             * 
             * @return int32_t 
             */
            virtual int32_t timestamp() = 0;
    };

    /**
     * @brief The "detail" namespace contains implementation
     *        details of the carp library. Do not call functions
     *        from that namespace directly, only use the provided
     *        top level interface functions in carp::
     * 
     */
    namespace detail
    {
        IWriter* the_writer{nullptr};
        ITimeStampProvider* timestamp_provider{nullptr};        

        enum class TypeId
        {
            i8 = 'b',
            i16 = 'i',
            i32 = 'I',
            u8 = 'B',
            u16 = 'u',
            u32 = 'U',
            f32 = 'F',
            f64 = 'D',
            string = 'S'
        };

        template<typename T>
        union ByteAccessor
        {
            T data;
            char bytes[sizeof(T)];

            char * begin() { return bytes; }
            size_t size() { return sizeof(T);}
        };

        class IByteCollection
        {
            public: 
            virtual ~IByteCollection() = default;
            virtual size_t size() = 0;
            virtual char* begin() = 0;
        };

        template<typename T>
        class GenericByteCollection : public IByteCollection
        {
            public:
            static GenericByteCollection<T> create(T data) { return GenericByteCollection<T>(data); }

            GenericByteCollection(T data_): data{data_} {}
            size_t size() override { return data.size(); }
            char* begin() override { return data.begin(); }

            private:
            ByteAccessor<T> data;
        };

        void write_bytes(IByteCollection& bytes)
        {
            the_writer->write(bytes.begin(), bytes.size());
        }

        template<typename first, typename... rest>
        void write(first f, rest... r)
        {
            write(f);
            write(r...);
        }

        template<typename T>
        void write( T data)
        {
            static_assert(false, "T is not supported");
        }        

        template<>
        void write<const char*>( const char* data)
        {
            constexpr auto type_id = static_cast<uint8_t>(TypeId::string);            
            write_bytes(GenericByteCollection<uint8_t>(type_id));

            // We need to write the length of the string first.
            // note , that we limit the stringlength to 64k - this
            // is a reasonable limit, while 255 might be too little,
            // espcially in cases of strings where the raw string is
            // transmitted.
            write_bytes(GenericByteCollection<uint16_t>(static_cast<uint16_t>(strlen(data))));
            the_writer->write(const_cast<char*>(data), strlen(data));            

        }

        template<>
        void write<int8_t>(int8_t data)
        {
            constexpr auto type_id = static_cast<uint8_t>(TypeId::i8);                     
            write_bytes(GenericByteCollection<uint8_t>(type_id));
            write_bytes(GenericByteCollection<int8_t>(data));
        }

        template<>
        void write<int16_t>(int16_t data)
        {
            constexpr auto type_id = static_cast<uint8_t>(TypeId::i16);                     
            write_bytes(GenericByteCollection<uint8_t>(type_id));
            write_bytes(GenericByteCollection<int16_t>(data));
        }

        template<>
        void write<int32_t>(int32_t data)
        {
            constexpr auto type_id = static_cast<uint8_t>(TypeId::i32);                     
            write_bytes(GenericByteCollection<uint8_t>(type_id));
            write_bytes(GenericByteCollection<int32_t>(data));
        }

        
        template<>
        void write<uint8_t>(uint8_t data)
        {
            constexpr auto type_id = static_cast<uint8_t>(TypeId::u16);
            write_bytes(GenericByteCollection<uint8_t>(type_id));
            write_bytes(GenericByteCollection<uint8_t>(data));
        } 

        template<>
        void write<uint16_t>(uint16_t data)
        {
            constexpr auto type_id = static_cast<uint8_t>(TypeId::u16);
            write_bytes(GenericByteCollection<uint8_t>(type_id));
            write_bytes(GenericByteCollection<uint16_t>(data));
        } 

        template<>
        void write<uint32_t>(uint32_t data)
        {
            constexpr auto type_id = static_cast<uint8_t>(TypeId::u32);
            write_bytes(GenericByteCollection<uint8_t>(type_id));
            write_bytes(GenericByteCollection<uint32_t>(data));
        }    

        template<>
        void write<float>(float data)
        {
            constexpr auto type_id = static_cast<uint8_t>(TypeId::f32);
            write_bytes(GenericByteCollection<uint8_t>(type_id));
            write_bytes(GenericByteCollection<float>(data));
        }

        template<>
        void write<double>(double data)
        {
            constexpr auto type_id = static_cast<uint8_t>(TypeId::f64);
            write_bytes(GenericByteCollection<uint8_t>(type_id));
            write_bytes(GenericByteCollection<double>(data));
        }
    }

    /**
     * @brief Output a carp message to the setup writer.
     *        This function's thread-safety relies on the
     *        writer to provide thread safety for calls between
     *        begin_frame() and end_frame().
     * 
     * @tparam T 
     * @param timestamp 
     * @param domain_id 
     * @param message_id 
     * @param args 
     */
    template<typename ...T>
    void write(int domain_id, int message_id, T... args)
    {
        // Call "setup_logging" first!
        assert(detail::the_writer != nullptr);

        uint32_t timestamp = 0;
        if (detail::timestamp_provider != nullptr)
        {
            timestamp = detail::timestamp_provider->timestamp();
        }

        detail::the_writer->begin_frame();
        // These need to be written "raw", as
        // detail::write will always add type prefixes
        // which we don't want here.

        detail::write_bytes(detail::GenericByteCollection<uint32_t>(timestamp));
        detail::write_bytes(detail::GenericByteCollection<uint32_t>(domain_id));
        detail::write_bytes(detail::GenericByteCollection<uint32_t>(message_id));
        detail::write_bytes(detail::GenericByteCollection<uint8_t>(static_cast<uint8_t>(sizeof...(args))));
        detail::write(args...);
        detail::the_writer->end_frame();
    }

    /**
     * @brief Set the up logging object. Note that this function is
     *        not threadsafe. 
     * 
     * @param writer A pointer to an output like object. This object's 
     *               lifetime should be static. If that is not possible
     *               it must be at least as long as the final call to
     *               "carp::write". Otherwise the behavior is undefined.
     */
    void setup_logging(IWriter* writer)
    {
        // Parameter must be non-null
        assert(writer != nullptr); 
        // Already setup
        assert(detail::the_writer == nullptr); 

        detail::the_writer = writer;
    }
}

// Carp Macros for use with a CarpString file structure

// Unspecialized case that will just blow out a format string with all arguments appended.
// will work but is inefficient, since the whole string is transmitted, also no domain or message id.
// is added. A viewer should treat this (implicitly, detected by message id being 0) as a formatstring where: The first argument
// is the actually used format string and the following arguments are the format arguments.
#define CARP_LOG(fmt_string, ...) carp::write(0, 0, fmt_string, __VA_ARGS__ );

// Specialized version with domain and message id. Is generated from CARP_LOG macros by
// the carp db tool. We keep the original fmt string for easier identification of the 
// individual marco calls
#define CARP_DFMT(fmt_string, domain_id, message_id, ...) carp::write(domain_id, message_id, __VA_ARGS__ );

#endif

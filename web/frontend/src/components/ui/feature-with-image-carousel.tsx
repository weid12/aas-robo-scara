import { Badge } from "@/components/ui/badge";
import {
    Carousel,
    CarouselContent,
    CarouselItem,
    CarouselNext,
    CarouselPrevious,
} from "@/components/ui/carousel";

function Feature() {
    return (
        <div className="w-full py-20 lg:py-40">
            <div className="container mx-auto">
                <div className="grid grid-cols-1 lg:grid-cols-2 justify-end items-end  gap-10">
                    <div className="flex gap-4 flex-col items-start">
                        <div>
                            <Badge>Platform</Badge>
                        </div>
                        <div className="flex gap-2 flex-col">
                            <h2 className="text-xl md:text-3xl lg:text-5xl tracking-tighter lg:max-w-xl font-regular text-left">
                                This is the start of something new
                            </h2>
                            <p className="text-lg  max-w-xl lg:max-w-sm leading-relaxed tracking-tight text-muted-foreground  text-left">
                                Managing a small business today is already tough. Avoid further
                                complications by ditching outdated, tedious trade methods. Our
                                goal is to streamline SMB trade, making it easier and faster than
                                ever.
                            </p>
                        </div>
                    </div>
                    <div className="w-full max-w-full px-6">
                        <Carousel>
                            <CarouselContent>
                                {Array.from({ length: 5 }).map((_, index) => (
                                    <CarouselItem key={index}>
                                        <div className="flex rounded-md aspect-video bg-muted items-center justify-center p-6 relative overflow-hidden">
                                            <img
                                                src={`https://images.unsplash.com/photo-${[
                                                    "1581091226825-a6a2a5aee158", // Tech/Robot
                                                    "1531746790731-6c087fecd65a", // Industrial
                                                    "1580927752452-89d86da3fa0a", // Coding
                                                    "1563770095765-afda80a8363a", // Server
                                                    "1518770660439-4636190af475"  // Chip
                                                ][index]}?auto=format&fit=crop&w=800&q=80`}
                                                alt={`Platform Screenshot ${index + 1}`}
                                                className="absolute inset-0 w-full h-full object-cover rounded-md"
                                            />
                                            <span className="text-sm text-white z-10 bg-black/50 px-2 py-1 rounded">
                                                Platform Screenshot {index + 1}
                                            </span>
                                        </div>
                                    </CarouselItem>
                                ))}
                            </CarouselContent>
                            <CarouselPrevious />
                            <CarouselNext />
                        </Carousel>
                    </div>
                </div>
            </div>
        </div>
    );
}

export { Feature };

const findResponseByKeywords = (message) => {
  // Check for keywords in the message
  const lowercaseMessage = message.toLowerCase();
  
  if (lowercaseMessage.includes('hello') || lowercaseMessage.includes('hi')) {
    return JSON.stringify({ message: chatResponses.hello });
  }
  if (lowercaseMessage.includes('tokyo')) {
    return JSON.stringify({ message: chatResponses.tokyo });
  }
  if (lowercaseMessage.includes('los angeles') || lowercaseMessage.includes('la')) {
    return JSON.stringify({ message: chatResponses.los_angeles });
  }
  if (lowercaseMessage.includes('hollywood')) {
    return JSON.stringify({ message: chatResponses.hollywood });
  }
  if (lowercaseMessage.includes('budget')) {
    return JSON.stringify({ message: chatResponses.budget });
  }
  if (lowercaseMessage.includes('flight')) {
    return JSON.stringify({ message: chatResponses.flight });
  }
  if (lowercaseMessage.includes('itinerary')) {
    return JSON.stringify({ message: chatResponses.itinerary });
  }
  if (lowercaseMessage.includes('hotel') || lowercaseMessage.includes('ritz')) {
    return JSON.stringify({ message: chatResponses.hotel });
  }
  if (lowercaseMessage.includes('food') || lowercaseMessage.includes('restaurant') || lowercaseMessage.includes('dining')) {
    return JSON.stringify({ message: chatResponses.food });
  }
  if (lowercaseMessage.includes('activity') || lowercaseMessage.includes('attraction') || 
      lowercaseMessage.includes('universal') || lowercaseMessage.includes('getty') || 
      lowercaseMessage.includes('dodger') || lowercaseMessage.includes('griffith')) {
    return JSON.stringify({ message: chatResponses.activity });
  }
  
  return JSON.stringify({ message: chatResponses.default });
}; 